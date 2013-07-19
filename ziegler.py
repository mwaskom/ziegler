import os
import sys
import os.path as op
import argparse
import numpy as np
import pandas as pd

from flask import Flask, request, render_template

from lyman import gather_project_info, gather_experiment_info

project = gather_project_info()
default_exp = project["default_exp"]

parser = argparse.ArgumentParser()
parser.add_argument("-experiment", default=default_exp)
parser.add_argument("-port", type=int, default=5000)
parser.add_argument("-external", action="store_true")
parser.add_argument("-debug", action="store_true")
args = parser.parse_args(sys.argv[1:])

exp = gather_experiment_info(args.experiment)

app = Flask(__name__)


def basic_info():
    """Basic information needed before any report options are set."""
    lyman_dir = os.environ["LYMAN_DIR"]

    subjects = np.loadtxt(op.join(lyman_dir, "subjects.txt"), str).tolist()
    selector_size = min(len(subjects), 10)

    runs = range(1, exp["n_runs"] + 1)

    contrasts = [c[0] for c in exp["contrasts"]]
    contrast_size = len(contrasts)

    return dict(all_subjects=subjects,
                selector_size=selector_size,
                experiment=args.experiment,
                runs=runs,
                all_contrasts=contrasts,
                contrast_size=contrast_size)


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
        if request.form.get("btn", "") == "Generate With Link":
            url = request.url + "?"
            args = ["=".join([k, v]) for k, v in request.form.iteritems()
                    if k != "btn"
                    and not (k == "space"
                             and not (request.form.getlist("ffx")
                                      or request.form.getlist("group")))]
            url += "&".join(args)
            info["report_url"] = unicode(url)

        # Populate info off the form values
        info = request_to_info(request.form, info)

    else:

        # Populate info for a group report
        if arg1 == "group":
            info["group"] = ["mask", "zstat", "peaks", "boxplot"]
            info["space"] = "mni"
            if arg2 is None:
                info["contrasts"] = info["all_contrasts"]
            else:
                info["contrasts"] = [arg2]

        # Populate info for a subject report
        elif arg1 is not None:
            info["subjects"] = [] if arg1 is None else [arg1]
            info["anatomy"] = ["anatwarp"]
            info["preproc"] = ["realign", "mc_target", "mean_func",
                               "art", "coreg"]
            info["model"] = ["design_mat", "design_corr",
                             "residuals", "zstats"]
            info["ffx"] = ["mask", "zstat"]
            info["space"] = "mni" if arg2 is None else arg2
            info["contrasts"] = info["all_contrasts"]

        # Populate info off the arguments
        else:
            info = request_to_info(request.args, info)

    return render_template("report.html", **info)


@app.template_filter("csv_to_html")
def cluster_csv_to_html(csv_file):
    """Read the csv file with peak information and generate an html table."""
    df = pd.read_csv(str(csv_file), index_col="Peak")
    df = df.reset_index()
    df["Peak"] += 1
    html = df.to_html(index=False, classes=["table",
                                            "table-striped",
                                            "table-condensed"])
    html = html.replace('border="1"', '')
    html = html.replace('class="dataframe ', 'class="')
    return html


def request_to_info(req, info):
    """Given a request multidict, populate the info dict."""
    for key in ["subjects", "anatomy", "preproc", "model",
                "ffx", "group", "contrasts"]:
        info[key] = req.getlist(key)
    info["space"] = req.get("space", "")

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


if __name__ == "__main__":
    try:
        link_source()
        host = None
        if args.external:
            host = "0.0.0.0"
            args.debug = False
        app.run(host=host, debug=args.debug, port=args.port)
    finally:
        unlink_source()
