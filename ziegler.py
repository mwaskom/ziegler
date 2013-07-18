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
@app.route("/report/<subj>", methods=["GET", "POST"])
@app.route("/report/<subj>/<space>", methods=["GET", "POST"])
def generate_report(subj=None, space=None):
    """Build the main report."""
    info = basic_info()

    if request.method == "POST":
        info["subjects"] = request.form.getlist("subjects")
        info["anatomy"] = request.form.getlist("anatomy")
        info["preproc"] = request.form.getlist("preproc")
        info["model"] = request.form.getlist("model")
        info["ffx"] = request.form.getlist("ffx")
        info["space"] = request.form["space"]
        info["group"] = request.form.getlist("group")
        info["contrasts"] = request.form.getlist("contrasts")
    else:
        info["subjects"] = [] if subj is None else [subj]
        info["anatomy"] = ["anatwarp"]
        info["preproc"] = ["realign", "mc_target", "mean_func", "art", "coreg"]
        info["model"] = ["design_mat", "design_corr", "residuals", "zstats"]
        info["ffx"] = ["mask", "zstat"]
        info["space"] = "mni" if space is None else space
        info["contrasts"] = info["all_contrasts"]

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
