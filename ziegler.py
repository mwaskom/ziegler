import os
import sys
import os.path as op
from glob import glob
import argparse
import subprocess as sp
import pandas as pd

from flask import Flask, request, render_template, send_file

import lyman

project = lyman.gather_project_info()
default_exp = project["default_exp"]

parser = argparse.ArgumentParser()
parser.add_argument("-subjects", nargs="*")
parser.add_argument("-experiment", default=default_exp)
parser.add_argument("-port", type=int, default=5000)
parser.add_argument("-external", action="store_true")
parser.add_argument("-debug", action="store_true")
args = parser.parse_args(sys.argv[1:])

exp = lyman.gather_experiment_info(args.experiment)
subjects = lyman.determine_subjects(args.subjects)

app = Flask(__name__)


def basic_info():
    """Basic information needed before any report options are set."""
    subjects_size = min(len(subjects), 10)

    runs = range(1, exp["n_runs"] + 1)

    contrasts = exp["contrast_names"]
    contrast_size = len(contrasts)

    all_rois = glob("static/data/*/masks/*.png")
    all_rois = [op.splitext(op.basename(m))[0] for m in all_rois]
    all_rois = sorted(list(set(all_rois)))
    roi_size = min(len(all_rois), 10)

    any_anatomy = (bool(glob("static/data/*/snapshots")) or
                   bool(glob("static/data/*/normalization")))
    any_preproc = bool(glob("static/analysis/*/preproc"))
    any_model = bool(glob("static/analysis/*/model"))
    any_ffx = bool(glob("static/analysis/*/ffx"))
    any_rois = bool(glob("static/data/*/masks"))
    any_group = bool(glob("static/analysis/*/mni"))
    any_contrasts = any_model or any_ffx or any_group

    return dict(all_subjects=subjects,
                subjects_size=subjects_size,
                experiment=args.experiment,
                runs=runs,
                all_contrasts=contrasts,
                contrast_size=contrast_size,
                all_rois=all_rois,
                roi_size=roi_size,
                any_anatomy=any_anatomy,
                any_preproc=any_preproc,
                any_model=any_model,
                any_ffx=any_ffx,
                any_rois=any_rois,
                any_group=any_group,
                any_contrasts=any_contrasts,
                )


@app.route("/")
def home():
    """Build the selector column."""
    info = basic_info()
    return render_template("layout.html", **info)


@app.route("/report", methods=["GET", "POST"])
@app.route("/report/<arg1>", methods=["GET", "POST"])
@app.route("/report/<arg1>/<arg2>", methods=["GET", "POST"])
def generate_report(arg1=None, arg2=None):
    """Build the main report."""
    info = basic_info()

    if request.method == "POST":

        # Possibly generate a url for the report
        form = request.form
        if form.get("btn", "") == "Generate With Link":
            args = ""
            for key in form:
                if key == "btn":
                    continue
                elif key == "space" and not (form.getlist("ffx")
                                             or form.getlist("group")):
                    continue
                elif key == "groupname" and not form.getlist("group"):
                    continue
                elif key == "contrasts" and not (form.getlist("model")
                                                 or form.getlist("ffx")
                                                 or form.getlist("group")):
                    continue
                for value in form.getlist(key):
                    args += "%s=%s&" % (key, value)
            url = request.url + "?" + args
            info["report_url"] = unicode(url)

        # Populate info off the form values
        info = request_to_info(request.form, info)

    else:

        # Populate info for a group report
        if arg1 == "group":
            info["group"] = ["mask", "zstat", "peaktable",
                             "peakimage", "boxplot", "watershed"]
            info["groupname"] = "group"
            info["space"] = "mni"
            if arg2 is None:
                info["contrasts"] = info["all_contrasts"]
            else:
                info["contrasts"] = [arg2]

        # Populate info for a subject report
        elif arg1 is not None:
            info["subjects"] = [] if arg1 is None else [arg1]
            info["anatomy"] = ["surfaces", "surfwarp", "volume",
                               "aseg", "anatwarp"]
            info["preproc"] = ["realign", "mc_target", "mean_func",
                               "art", "coreg"]
            info["model"] = ["design_mat", "confound_corr", "svd",
                             "residuals", "r2s", "filter", "zstats"]
            info["ffx"] = ["mask", "r2s", "zstat"]
            info["space"] = "mni" if arg2 is None else arg2
            info["contrasts"] = info["all_contrasts"]

        # Populate info off the arguments
        else:
            info = request_to_info(request.args, info)

    # Possibly generate a PDF
    if request.form.get("btn", "") == "Download PDF Report":
        info["reportonly"] = True
        html = render_template("report.html", **info)
        html = html.replace("/static", "static")

        with open("report.html", "w") as fid:
            fid.write(html)

        try:
            sp.check_output(["pandoc", "report.html",
                             "-V", "geometry:margin=.75in",
                             "-o", "report.pdf"])
        except sp.CalledProcessError:
            return render_template("layout.html",
                                    pandocfail=True,
                                    **basic_info())
        return send_file("report.pdf")

    return render_template("report.html", **info)


@app.route("/viewer")
def viewer():
    info = basic_info()
    info["javascript"] = True

    viewdata = []
    urls = request.args.getlist("url")
    names = request.args.getlist("name")
    palettes = request.args.getlist("palette")
    signs = request.args.getlist("sign")
    visibles = request.args.getlist("visible")
    pos_threshes = request.args.getlist("pos_thresh")
    neg_threshes = request.args.getlist("neg_thresh")

    datazip = zip(urls, names, palettes, signs, visibles,
                  pos_threshes, neg_threshes)
    for data in datazip:
        keys = ["url", "name", "palette", "sign", "visible",
                "pos_thresh", "neg_thresh"]
        data_dict = dict(zip(keys, data))
        viewdata.append(data_dict)

    info["viewdata"] = viewdata

    info["source"] = request.args.get("source")
    info["contrast"] = request.args.get("contrast")

    return render_template("viewer.html", **info)


@app.template_filter("csv_to_html")
def cluster_csv_to_html(csv_file):
    """Read the csv file with peak information and generate an html table."""
    try:
        df = pd.read_csv(str(csv_file), index_col="Peak")
    except IOError:
        return "<p>Could not read %s </p><br>" % csv_file

    if not len(df):
        return "<p>No significant clusters</p><br>"

    df = df.reset_index()
    df["Peak"] += 1
    html = df.to_html(index=False, classes=["table",
                                            "table-striped",
                                            "table-condensed"])
    html = html.replace('border="1"', '')
    html = html.replace('class="dataframe ', 'class="')
    return html


@app.template_filter("thresh_pos")
def thresh_pos(palette):
    return 0 if palette == "grayscale" else 2.3


@app.template_filter("thresh_neg")
def thresh_neg(palette):
    return 0 if palette == "grayscale" else -2.3


def request_to_info(req, info):
    """Given a request multidict, populate the info dict."""
    keys = ["subjects", "anatomy", "preproc", "model", "ffx",
            "rois", "group", "contrasts"]
    for key in keys:
        info[key] = req.getlist(key)
    info["space"] = req.get("space", "")
    groupname = req.get("groupname", "group")
    info["groupname"] = groupname if groupname else "group"

    return info


def link_source():
    """Link source directories to static/."""
    unlink_source()
    os.symlink(op.join(project["analysis_dir"], args.experiment),
               "static/analysis")
    os.symlink(project["data_dir"], "static/data")


def unlink_source():
    """Remove source directories from static/, if they exist."""
    if op.exists("static/data"):
        os.unlink("static/data")
    if op.exists("static/analysis"):
        os.unlink("static/analysis")


def clean_up():
    """Remove files that get created during runtime."""
    unlink_source()
    for ext in ["html", "pdf"]:
        fname = "report." + ext
        if op.exists(fname):
            os.remove(fname)


if __name__ == "__main__":
    try:
        link_source()
        host = None
        if args.external:
            host = "0.0.0.0"
            args.debug = False
        app.run(host=host, debug=args.debug, port=args.port)
    finally:
        clean_up()
