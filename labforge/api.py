"""
HTTP surface.

Every route takes a spec and returns JSON. The browser never sends code,
never sends SQL and never sends a command line; it sends the id of a
registry entry plus values for that entry's declared fields.
"""

import json
import os
import shutil
import time

from flask import Flask, Response, jsonify, request, send_file

from . import (APP_NAME, APP_TAGLINE, APP_VERSION, config, datasets, db, harvest,
               jobs, library, plots_registry, plots_run, reporting, screening,
               stats_registry, stats_run)
from .jobs import BUS, JOBS, sse


def create_app():
    app = Flask(__name__)
    db.init()

    # ── shell ────────────────────────────────────────────────────────────
    @app.get("/")
    def index():
        from .ui.html import page
        return Response(page(), mimetype="text/html")

    @app.get("/api/bootstrap")
    def bootstrap():
        """Everything the client needs to build itself."""
        return jsonify({
            "app": {"name": APP_NAME, "version": APP_VERSION, "tagline": APP_TAGLINE},
            "config": config.CONFIG,
            "defaults": config.DEFAULT_CONFIG,
            "deps": config.dependency_report(),
            "tests": {"groups": stats_registry.GROUPS, "entries": stats_registry.REGISTRY},
            "plots": {"groups": plots_registry.GROUPS, "entries": plots_registry.REGISTRY,
                      "common": plots_registry.COMMON,
                      "presets": plots_registry.JOURNAL_PRESETS,
                      "palettes": plots_registry.PALETTES},
            "sources": {"groups": harvest.GROUPS, "entries": harvest.REGISTRY},
            "instruments": screening.INSTRUMENTS,
            "forms": {k: {"label": v["label"], "fields": v["fields"]}
                      for k, v in screening.DEFAULT_FORMS.items()},
            "checklists": {k: v["label"] for k, v in reporting.CHECKLISTS.items()},
            "exclusion_reasons": screening.EXCLUSION_REASONS,
            "library": library.grouped(),
            "reset_scopes": [{"id": k, "label": v[0], "description": v[1]}
                             for k, v in RESET_SCOPES.items()],
            "transforms": datasets.TRANSFORMS,
            "outlier_methods": datasets.OUTLIER_METHODS,
            "counts": {"tests_ready": stats_registry.ready_count(),
                       "tests_total": len(stats_registry.TESTS),
                       "plots_total": len(plots_registry.PLOTS),
                       "sources_total": len(harvest.SOURCES)},
        })

    @app.post("/api/config")
    def set_config():
        return jsonify(config.update(request.json or {}))

    # ── datasets ─────────────────────────────────────────────────────────
    @app.get("/api/datasets")
    def list_ds():
        return jsonify(datasets.list_datasets())

    @app.post("/api/datasets/upload")
    def upload_ds():
        f = request.files.get("file")
        if not f:
            return jsonify({"error": "No file received."}), 400
        tmp = os.path.join(config.TMP_DIR, f.filename)
        f.save(tmp)
        try:
            ds_id = datasets.import_file(tmp, name=f.filename)
        except Exception as exc:
            return jsonify({"error": f"{type(exc).__name__}: {exc}"}), 400
        return jsonify(datasets.meta(ds_id))

    @app.post("/api/datasets/path")
    def path_ds():
        p = (request.json or {}).get("path", "")
        if not os.path.exists(p):
            return jsonify({"error": f"No file at {p}"}), 400
        try:
            return jsonify(datasets.meta(datasets.import_file(p)))
        except Exception as exc:
            return jsonify({"error": f"{type(exc).__name__}: {exc}"}), 400

    @app.get("/api/datasets/<ds_id>")
    def get_ds(ds_id):
        m = datasets.meta(ds_id)
        if not m:
            return jsonify({"error": "Not found"}), 404
        df = datasets.load(ds_id)
        m["preview"] = json.loads(df.head(200).to_json(orient="records", date_format="iso"))
        return jsonify(m)

    @app.post("/api/datasets/<ds_id>/dictionary")
    def set_dict(ds_id):
        return jsonify(datasets.set_dictionary(ds_id, request.json or {}))

    @app.get("/api/datasets/<ds_id>/missing")
    def ds_missing(ds_id):
        return jsonify(datasets.missingness(ds_id))

    @app.post("/api/datasets/<ds_id>/deident")
    def ds_deident(ds_id):
        qi = (request.json or {}).get("quasi_identifiers") or []
        return jsonify(datasets.deident_check(ds_id, qi))

    @app.delete("/api/datasets/<ds_id>")
    def del_ds(ds_id):
        """Remove a dataset. Its runs are kept unless asked for, because the
        ledger is evidence: deleting the data should not silently erase the
        record that the analyses happened."""
        also_runs = request.args.get("runs") == "1"
        m = datasets.meta(ds_id)
        n_runs = db.runs_on_dataset(m["sha256"]) if m else 0
        if m and m.get("path") and os.path.exists(m["path"]):
            try:
                os.remove(m["path"])
            except OSError:
                pass
        datasets._cache.pop(ds_id, None)
        db.exec_("DELETE FROM dataset_op WHERE dataset_id=?", (ds_id,))
        db.exec_("DELETE FROM dataset WHERE id=?", (ds_id,))
        if also_runs and m:
            db.exec_("DELETE FROM analysis_run WHERE dataset_sha=?", (m["sha256"],))
        return jsonify({"ok": True, "runs_kept": 0 if also_runs else n_runs,
                        "runs_deleted": n_runs if also_runs else 0})

    # ── statistics ───────────────────────────────────────────────────────
    @app.post("/api/preflight")
    def api_preflight():
        try:
            return jsonify(stats_run.preflight(request.json or {}))
        except Exception as exc:
            return jsonify({"ok": False, "errors": [f"{type(exc).__name__}: {exc}"]}), 400

    @app.post("/api/run")
    def api_run():
        spec = request.json or {}
        heavy = spec.get("test") in ("permutation_two", "bootstrap_diff", "power_sim",
                                     "classifier_eval", "network_meta")
        if heavy or spec.get("as_job"):
            entry = stats_registry.get(spec.get("test")) or {}
            job = JOBS.submit("analysis", entry.get("label", spec.get("test", "Analysis")),
                              lambda ctl: stats_run.run(spec, ctl), spec)
            return jsonify({"job": job.id, "queued": True})
        try:
            return jsonify(stats_run.run(spec))
        except stats_run.NotImplementedRunner as exc:
            return jsonify({"ok": False, "not_implemented": True,
                            "errors": [str(exc)]}), 501
        except Exception as exc:
            return jsonify({"ok": False, "errors": [f"{type(exc).__name__}: {exc}"]}), 400

    @app.get("/api/runs")
    def api_runs():
        rows = db.query("SELECT id, test_id, status, created_at, duration_ms, note, "
                        "dataset_id, dataset_sha FROM analysis_run "
                        "ORDER BY created_at DESC LIMIT 300")
        return jsonify(rows)

    @app.get("/api/runs/<run_id>")
    def api_run_detail(run_id):
        r = db.one("SELECT * FROM analysis_run WHERE id=?", (run_id,))
        if not r:
            return jsonify({"error": "Not found"}), 404
        for k in ("spec", "result", "assumptions", "versions"):
            try:
                r[k] = json.loads(r[k] or "null")
            except Exception:
                pass
        return jsonify(r)

    @app.delete("/api/runs/<run_id>")
    def del_run(run_id):
        """Delete one entry from the provenance ledger, and every figure that
        was drawn from it. The count of what went is returned so the interface
        can say what it did rather than just going quiet."""
        figs = db.query("SELECT * FROM figure WHERE run_id=?", (run_id,))
        for f in figs:
            _unlink_fig(f)
        db.exec_("DELETE FROM figure WHERE run_id=?", (run_id,))
        db.exec_("DELETE FROM analysis_run WHERE id=?", (run_id,))
        return jsonify({"ok": True, "figures_deleted": len(figs)})

    @app.post("/api/runs/clear")
    def clear_runs():
        """Scope: all | dataset | failed | blocked | before. Clearing the whole
        ledger resets the multiplicity audit, so the response says so."""
        b = request.json or {}
        scope = b.get("scope", "all")
        where, args = "1=1", []
        if scope == "dataset" and b.get("dataset"):
            m = datasets.meta(b["dataset"])
            where, args = "dataset_sha=?", [m["sha256"] if m else ""]
        elif scope == "failed":
            where = "status='failed'"
        elif scope == "blocked":
            where = "status='blocked'"
        elif scope == "before" and b.get("before"):
            where, args = "created_at < ?", [float(b["before"])]
        ids = [r["id"] for r in db.query(f"SELECT id FROM analysis_run WHERE {where}",
                                         tuple(args))]
        for f in db.query("SELECT * FROM figure"):
            if f["run_id"] in ids:
                _unlink_fig(f)
                db.exec_("DELETE FROM figure WHERE id=?", (f["id"],))
        db.exec_(f"DELETE FROM analysis_run WHERE {where}", tuple(args))
        return jsonify({"ok": True, "deleted": len(ids), "scope": scope,
                        "note": ("The multiplicity audit now counts from zero. "
                                 "That is the point of clearing it, but it also means "
                                 "the tests you ran before this are no longer recorded."
                                 if scope == "all" else None)})

    def _unlink_fig(f):
        if f.get("path") and os.path.exists(f["path"]):
            try:
                os.remove(f["path"])
            except OSError:
                pass

    # ── plots ────────────────────────────────────────────────────────────
    @app.post("/api/plot")
    def api_plot():
        body = request.json or {}
        run_id = body.get("run_id")
        result = body.get("result")
        if run_id and not result:
            r = db.one("SELECT * FROM analysis_run WHERE id=?", (run_id,))
            if not r:
                return jsonify({"error": "Run not found"}), 404
            result = json.loads(r["result"] or "{}")
            result["run_id"] = run_id
            spec = json.loads(r["spec"] or "{}")
        else:
            spec = body.get("spec") or {}
        data = _raw_for_plot(spec, result, body.get("plot"))
        try:
            path = plots_run.render(body.get("plot"), result, body.get("params") or {}, data)
        except NotImplementedError as exc:
            return jsonify({"error": str(exc), "not_implemented": True}), 501
        except Exception as exc:
            return jsonify({"error": f"{type(exc).__name__}: {exc}"}), 400
        return jsonify({"path": path, "url": f"/api/figure?path={path}",
                        "name": os.path.basename(path)})

    def _raw_for_plot(spec, result, plot_id):
        """Attach the raw values a plot needs but a result dict does not carry."""
        try:
            df = datasets.load(spec.get("dataset")) if spec.get("dataset") else None
        except Exception:
            return None
        if df is None:
            return None
        roles = spec.get("roles") or {}

        def first(k):
            v = roles.get(k)
            return v[0] if isinstance(v, list) and v else v

        import pandas as pd
        dv, group = first("dv"), first("group")
        if dv and group and dv in df.columns and group in df.columns:
            out = {}
            for lvl, sub in df.groupby(group, dropna=True, observed=True):
                out[str(lvl)] = pd.to_numeric(sub[dv], errors="coerce").dropna().tolist()
            return out
        if plot_id in ("qq", "hist"):
            col = dv or first("vars") or (roles.get("vars") or [None])[0]
            if col and col in df.columns:
                return {"values": pd.to_numeric(df[col], errors="coerce").dropna().tolist(),
                        "label": col}
        if plot_id == "scatter_fit":
            vs = roles.get("vars") or []
            if len(vs) >= 2:
                pair = df[vs[:2]].apply(pd.to_numeric, errors="coerce").dropna()
                return {"x": pair[vs[0]].tolist(), "y": pair[vs[1]].tolist(),
                        "xlabel": vs[0], "ylabel": vs[1]}
        return None

    @app.get("/api/figure")
    def api_figure():
        p = request.args.get("path", "")
        if not p.startswith(config.FIG_DIR) or not os.path.exists(p):
            return jsonify({"error": "Not found"}), 404
        return send_file(p)

    @app.get("/api/figures")
    def api_figures():
        rows = db.query("SELECT * FROM figure ORDER BY created_at DESC LIMIT 200")
        for r in rows:
            r["exists"] = bool(r.get("path") and os.path.exists(r["path"]))
        return jsonify(rows)

    @app.delete("/api/figures/<fig_id>")
    def del_fig(fig_id):
        f = db.one("SELECT * FROM figure WHERE id=?", (fig_id,))
        if f:
            _unlink_fig(f)
            db.exec_("DELETE FROM figure WHERE id=?", (fig_id,))
        return jsonify({"ok": bool(f)})

    @app.post("/api/figures/clear")
    def clear_figs():
        rows = db.query("SELECT * FROM figure")
        for f in rows:
            _unlink_fig(f)
        db.exec_("DELETE FROM figure")
        return jsonify({"ok": True, "deleted": len(rows)})

    # ── harvest ──────────────────────────────────────────────────────────
    @app.post("/api/harvest")
    def api_harvest():
        body = request.json or {}
        sid = body.get("source")
        entry = harvest.REGISTRY.get(sid)
        if not entry:
            return jsonify({"error": f"Unknown source {sid!r}"}), 400
        params = body.get("params") or {}
        pid = body.get("project")
        job = JOBS.submit("harvest", f"{entry['label']} search",
                          lambda ctl: harvest.harvest(sid, params, pid, ctl), body)
        return jsonify({"job": job.id, "queued": True})

    @app.get("/api/records")
    def api_records():
        pid = request.args.get("project")
        q = request.args.get("q", "")
        sql = ("SELECT id, source, doi, title, authors, journal, year, retracted, oa_url, "
               "dedup_of FROM record WHERE project_id IS ?")
        args = [pid]
        if q:
            sql += " AND (title LIKE ? OR abstract LIKE ?)"
            args += [f"%{q}%", f"%{q}%"]
        sql += " ORDER BY year DESC LIMIT 500"
        return jsonify(db.query(sql, tuple(args)))

    @app.post("/api/dedup")
    def api_dedup():
        pid = (request.json or {}).get("project")
        job = JOBS.submit("dedup", "Deduplicating corpus",
                          lambda ctl: screening.deduplicate(pid, ctl=ctl))
        return jsonify({"job": job.id, "queued": True})

    @app.post("/api/records/preview")
    def records_preview():
        """Count what a trim would remove before it removes it. Narrowing a
        search after the fact is normal; doing it blind is not."""
        where, args = _record_filter(request.json or {})
        n = db.one(f"SELECT COUNT(*) c FROM record WHERE {where}", tuple(args))
        sample = db.query(f"SELECT title, year, source, doi FROM record WHERE {where} "
                          "ORDER BY year DESC LIMIT 12", tuple(args))
        total = db.one("SELECT COUNT(*) c FROM record", ())
        return jsonify({"matched": n["c"] if n else 0,
                        "total": total["c"] if total else 0,
                        "remaining": (total["c"] - n["c"]) if (total and n) else 0,
                        "sample": sample})

    @app.post("/api/records/delete")
    def records_delete():
        where, args = _record_filter(request.json or {})
        n = db.one(f"SELECT COUNT(*) c FROM record WHERE {where}", tuple(args))
        # Screening decisions, extractions and risk-of-bias rows cascade with
        # the record, so a trim cannot leave orphaned judgements behind.
        db.exec_(f"DELETE FROM record WHERE {where}", tuple(args))
        return jsonify({"ok": True, "deleted": n["c"] if n else 0})

    @app.delete("/api/records/<rec_id>")
    def del_record(rec_id):
        db.exec_("DELETE FROM record WHERE id=?", (rec_id,))
        return jsonify({"ok": True})

    def _record_filter(b):
        """Build a WHERE clause from the trim controls. Anything left blank is
        simply not applied, so an empty filter matches everything and the
        preview will say so loudly."""
        clauses, args = [], []
        if b.get("project") is not None:
            clauses.append("project_id IS ?"); args.append(b["project"])
        if b.get("ids"):
            marks = ",".join("?" for _ in b["ids"])
            clauses.append(f"id IN ({marks})"); args += list(b["ids"])
        if b.get("source"):
            clauses.append("source = ?"); args.append(b["source"])
        if b.get("query"):
            clauses.append("(title LIKE ? OR abstract LIKE ?)")
            args += [f"%{b['query']}%"] * 2
        if b.get("not_query"):
            clauses.append("(COALESCE(title,'') NOT LIKE ? AND COALESCE(abstract,'') NOT LIKE ?)")
            args += [f"%{b['not_query']}%"] * 2
        if b.get("year_before"):
            clauses.append("(year IS NULL OR year < ?)"); args.append(int(b["year_before"]))
        if b.get("year_after"):
            clauses.append("year > ?"); args.append(int(b["year_after"]))
        if b.get("no_abstract"):
            clauses.append("(abstract IS NULL OR abstract = '')")
        if b.get("retracted"):
            clauses.append("retracted > 0")
        if b.get("duplicates"):
            clauses.append("dedup_of IS NOT NULL")
        if b.get("unscreened"):
            clauses.append("id NOT IN (SELECT record_id FROM screen)")
        if b.get("excluded"):
            clauses.append("id IN (SELECT record_id FROM screen WHERE decision='exclude')")
        return (" AND ".join(clauses) if clauses else "1=1"), args

    # ── screening ────────────────────────────────────────────────────────
    @app.get("/api/screen/queue")
    def api_queue():
        return jsonify(screening.queue(
            request.args.get("project"),
            request.args.get("stage", "title_abstract"),
            request.args.get("reviewer"),
            int(request.args.get("limit", 50)),
            blind=request.args.get("blind", "1") != "0"))

    @app.post("/api/screen/decide")
    def api_decide():
        b = request.json or {}
        return jsonify(screening.decide(b["record_id"], b["decision"],
                                        b.get("stage", "title_abstract"),
                                        b.get("reviewer"), b.get("reason")))

    @app.post("/api/screen/undo")
    def api_undo():
        """Remove the most recent decision by this reviewer at this stage, so
        a mis-keyed include is genuinely retractable rather than just scrolled
        past."""
        b = request.json or {}
        row = db.one("SELECT s.*, r.title FROM screen s JOIN record r ON r.id=s.record_id "
                     "WHERE s.stage=? AND s.reviewer=? ORDER BY s.decided_at DESC LIMIT 1",
                     (b.get("stage", "title_abstract"), b.get("reviewer")))
        if not row:
            return jsonify({"ok": False, "message": "Nothing to undo at this stage."})
        db.exec_("DELETE FROM screen WHERE id=?", (row["id"],))
        return jsonify({"ok": True, "undone": row["decision"], "title": row["title"],
                        "record_id": row["record_id"]})

    @app.post("/api/screen/reset")
    def api_screen_reset():
        """Scope: stage | reviewer | all. Records are untouched; only the
        judgements go, so the corpus survives a restart of the screen."""
        b = request.json or {}
        scope = b.get("scope", "stage")
        if scope == "all":
            where, args = "1=1", []
        elif scope == "reviewer":
            where, args = "reviewer=?", [b.get("reviewer")]
        else:
            where, args = "stage=? AND reviewer=?", [b.get("stage", "title_abstract"),
                                                     b.get("reviewer")]
        n = db.one(f"SELECT COUNT(*) c FROM screen WHERE {where}", tuple(args))
        db.exec_(f"DELETE FROM screen WHERE {where}", tuple(args))
        return jsonify({"ok": True, "deleted": n["c"] if n else 0,
                        "note": "Records kept. Only the decisions were cleared."})

    @app.delete("/api/screen/<record_id>")
    def api_unscreen(record_id):
        db.exec_("DELETE FROM screen WHERE record_id=?", (record_id,))
        return jsonify({"ok": True})

    @app.delete("/api/extraction/<record_id>")
    def api_del_extraction(record_id):
        db.exec_("DELETE FROM extraction WHERE record_id=?", (record_id,))
        return jsonify({"ok": True})

    @app.delete("/api/rob/<record_id>")
    def api_del_rob(record_id):
        db.exec_("DELETE FROM rob WHERE record_id=?", (record_id,))
        return jsonify({"ok": True})

    @app.get("/api/screen/agreement")
    def api_agreement():
        return jsonify(screening.agreement(request.args.get("project"),
                                           request.args.get("stage", "title_abstract"),
                                           request.args.get("a"), request.args.get("b")))

    @app.get("/api/screen/prisma")
    def api_prisma():
        return jsonify(screening.prisma_counts(request.args.get("project")))

    @app.post("/api/extraction")
    def api_extract():
        b = request.json or {}
        return jsonify(screening.save_extraction(b["record_id"], b["form_id"],
                                                 b.get("payload") or {}))

    @app.get("/api/extraction")
    def api_extract_table():
        return jsonify(screening.extraction_table(request.args.get("form", "rct"),
                                                  request.args.get("project")))

    @app.get("/api/extraction/meta")
    def api_extract_meta():
        return jsonify(screening.to_meta_frame(request.args.get("form", "rct"),
                                               request.args.get("project"),
                                               request.args.get("measure", "SMD")))

    @app.post("/api/rob")
    def api_rob():
        b = request.json or {}
        return jsonify(screening.set_rob(b["record_id"], b["instrument"],
                                         b.get("domains") or {}, b.get("overall")))

    @app.get("/api/rob")
    def api_rob_summary():
        return jsonify(screening.rob_summary(request.args.get("instrument", "rob2"),
                                             request.args.get("project")))

    # ── library ──────────────────────────────────────────────────────────
    @app.get("/api/library")
    def api_library():
        return jsonify({"sections": library.grouped(),
                        "count": len(library.ENTRIES)})

    @app.get("/api/library/<entry_id>")
    def api_library_entry(entry_id):
        e = library.get(entry_id)
        return jsonify(e) if e else (jsonify({"error": "Not found"}), 404)

    @app.get("/api/library/search")
    def api_library_search():
        return jsonify(library.search(request.args.get("q", "")))

    # ── reviewers ────────────────────────────────────────────────────────
    @app.get("/api/reviewers")
    def api_reviewers():
        return jsonify(screening.reviewers())

    @app.post("/api/reviewers")
    def api_add_reviewer():
        b = request.json or {}
        if b.get("id"):
            return jsonify(screening.rename_reviewer(b["id"], b.get("name", "")))
        return jsonify(screening.add_reviewer(b.get("name", ""), b.get("role", "screener")))

    @app.delete("/api/reviewers/<rid>")
    def api_del_reviewer(rid):
        keep = request.args.get("decisions") != "0"
        return jsonify(screening.remove_reviewer(rid, keep_decisions=keep))

    @app.post("/api/screen/resolve")
    def api_resolve():
        b = request.json or {}
        return jsonify(screening.resolve(b["record_id"], b.get("stage", "title_abstract"),
                                         b["decision"], b.get("rationale", ""),
                                         b.get("by")))

    # ── reporting ────────────────────────────────────────────────────────
    @app.post("/api/report/sentence")
    def api_sentence():
        b = request.json or {}
        return jsonify({"text": reporting.sentence(b.get("result") or {}, b.get("style"))})

    @app.get("/api/report/methods")
    def api_methods():
        return jsonify(reporting.methods_paragraph(request.args.get("sha")))

    @app.get("/api/report/checklist/<kind>")
    def api_checklist(kind):
        try:
            return jsonify(reporting.checklist(kind))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.post("/api/report/bundle")
    def api_bundle():
        b = request.json or {}
        return jsonify(reporting.bundle(b.get("dataset"), b.get("include_data", True)))

    @app.post("/api/report/prereg")
    def api_prereg():
        b = request.json or {}
        return jsonify(reporting.prereg_draft(b.get("question", ""),
                                              b.get("outcomes", ""),
                                              b.get("hypotheses", "")))

    @app.get("/api/download")
    def api_download():
        p = request.args.get("path", "")
        if not (p.startswith(config.EXPORT_DIR) or p.startswith(config.FIG_DIR)) \
                or not os.path.exists(p):
            return jsonify({"error": "Not found"}), 404
        return send_file(p, as_attachment=True)

    # ── wholesale clearing ───────────────────────────────────────────────
    #
    # Everything above deletes one thing. This deletes a whole category, and
    # is deliberately the only place that can. Each scope reports what it would
    # remove before it removes it, so nothing here is a one-click surprise.

    RESET_SCOPES = {
        "cache":     ("Harvest cache", "Cached API responses. Safe: they refetch."),
        "figures":   ("Figures", "Rendered images on disk and their records."),
        "runs":      ("Run ledger", "Every analysis result and the multiplicity audit."),
        "screening": ("Screening decisions", "Include/exclude judgements. Records kept."),
        "extraction":("Extractions and risk of bias", "Extracted data and RoB judgements."),
        "corpus":    ("Corpus", "All harvested records, and everything attached to them."),
        "datasets":  ("Datasets", "Imported data files. Runs are kept."),
        "everything":("Everything", "Full reset back to a first launch."),
    }

    @app.get("/api/reset/scopes")
    def reset_scopes():
        out = []
        for key, (label, desc) in RESET_SCOPES.items():
            out.append({"id": key, "label": label, "description": desc,
                        "count": _reset_count(key)})
        return jsonify(out)

    def _reset_count(scope):
        one = lambda q: (db.one(q, ()) or {}).get("c", 0)
        if scope == "figures":
            return one("SELECT COUNT(*) c FROM figure")
        if scope == "runs":
            return one("SELECT COUNT(*) c FROM analysis_run")
        if scope == "screening":
            return one("SELECT COUNT(*) c FROM screen")
        if scope == "extraction":
            return one("SELECT COUNT(*) c FROM extraction") + one("SELECT COUNT(*) c FROM rob")
        if scope == "corpus":
            return one("SELECT COUNT(*) c FROM record")
        if scope == "datasets":
            return one("SELECT COUNT(*) c FROM dataset")
        if scope == "cache":
            try:
                return len(os.listdir(config.CACHE_DIR))
            except OSError:
                return 0
        if scope == "everything":
            return sum(_reset_count(k) for k in RESET_SCOPES if k != "everything")
        return 0

    @app.post("/api/reset")
    def do_reset():
        b = request.json or {}
        scope = b.get("scope")
        if scope not in RESET_SCOPES:
            return jsonify({"error": f"Unknown scope {scope!r}."}), 400
        if b.get("confirm") is not True:
            return jsonify({"error": "This needs an explicit confirmation.",
                            "would_delete": _reset_count(scope)}), 400
        n = _reset_count(scope)
        targets = [scope] if scope != "everything" else \
            [k for k in RESET_SCOPES if k != "everything"]
        for t in targets:
            if t == "figures":
                for f in db.query("SELECT * FROM figure"):
                    _unlink_fig(f)
                db.exec_("DELETE FROM figure")
            elif t == "runs":
                db.exec_("DELETE FROM analysis_run")
            elif t == "screening":
                db.exec_("DELETE FROM screen")
            elif t == "extraction":
                db.exec_("DELETE FROM extraction")
                db.exec_("DELETE FROM rob")
            elif t == "corpus":
                db.exec_("DELETE FROM record")
                db.exec_("DELETE FROM harvest_query")
            elif t == "datasets":
                for d in db.query("SELECT * FROM dataset"):
                    if d.get("path") and os.path.exists(d["path"]):
                        try:
                            os.remove(d["path"])
                        except OSError:
                            pass
                datasets._cache.clear()
                db.exec_("DELETE FROM dataset_op")
                db.exec_("DELETE FROM dataset")
            elif t == "cache":
                for name in os.listdir(config.CACHE_DIR):
                    try:
                        os.remove(os.path.join(config.CACHE_DIR, name))
                    except OSError:
                        pass
        return jsonify({"ok": True, "scope": scope, "deleted": n})

    # ── jobs ─────────────────────────────────────────────────────────────
    @app.get("/api/jobs")
    def api_jobs():
        return jsonify(JOBS.list())

    @app.get("/api/jobs/<jid>")
    def api_job(jid):
        j = JOBS.get(jid)
        return jsonify(j.to_dict(with_log=True)) if j else (jsonify({"error": "gone"}), 404)

    @app.post("/api/jobs/<jid>/cancel")
    def api_cancel(jid):
        j = JOBS.get(jid)
        if j:
            j.cancel()
        return jsonify({"ok": bool(j)})

    @app.post("/api/jobs/clear")
    def api_clear():
        JOBS.clear_finished()
        return jsonify({"ok": True})

    @app.get("/api/events")
    def api_events():
        def stream():
            q = BUS.subscribe()
            try:
                yield sse({"type": "hello", "t": time.time()})
                while True:
                    try:
                        yield sse(q.get(timeout=20))
                    except Exception:
                        yield ": keepalive\n\n"
            finally:
                BUS.unsubscribe(q)
        return Response(stream(), mimetype="text/event-stream",
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True, "version": APP_VERSION,
                        "deps_missing": [d["pip"] for d in config.dependency_report()
                                         if not d["ok"] and d["required"]]})

    return app
