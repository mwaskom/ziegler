import os
import sys
import os.path as op
import argparse
import numpy as np

from flask import Flask, request, render_template

from lyman import gather_project_info, gather_experiment_info

parser = argparse.ArgumentParser()
parser.add_argument("experiment")
parser.add_argument("-debug", action="store_true")
parser.add_argument("-port", type=int, default=5000)
args = parser.parse_args(sys.argv[1:])

project = gather_project_info()
if args.experiment is None:
    args.experiment = project["default_exp"]
exp = gather_experiment_info(args.experiment)

app = Flask(__name__)


@app.route("/")
def home():

    info = subject_info()
    contrasts = [c[0] for c in exp["contrasts"]]
    info["all_contrasts"] = contrasts
    info["contrast_size"] = len(contrasts)
    return render_template("layout.html", **info)


@app.route("/report", methods=["GET", "POST"])
@app.route("/report/<subj>", methods=["GET", "POST"])
def generate_report(subj=None):

    info = subject_info()
    info["runs"] = range(1, exp["n_runs"] + 1)

    contrasts = [c[0] for c in exp["contrasts"]]
    info["all_contrasts"] = contrasts
    info["contrast_size"] = len(contrasts)

    if request.method == "POST":
        info["subjects"] = request.form.getlist("subjects")
        info["anatomy"] = request.form.getlist("anatomy")
        info["preproc"] = request.form.getlist("preproc")
        info["model"] = request.form.getlist("model")
        info["ffx"] = request.form.getlist("ffx")
        info["group"] = request.form.getlist("group")
        info["contrasts"] = request.form.getlist("contrasts")
    else:
        info["subjects"] = [] if subj is None else [subj]
        info["anatomy"] = ["anatwarp"]
        info["preproc"] = ["realign", "mc_target", "mean_func", "art", "coreg"]
        info["model"] = ["design_mat", "design_corr", "residuals", "zstats"]
        info["ffx"] = ["mask", "zstat"]
        info["contrasts"] = info["all_contrasts"]

    return render_template("report.html", **info)


def subject_info():

    lyman_dir = os.environ["LYMAN_DIR"]
    subjects = np.loadtxt(op.join(lyman_dir, "subjects.txt"), str).tolist()
    selector_size = min(len(subjects), 20)

    return dict(all_subjects=subjects,
                selector_size=selector_size,
                exp=args.experiment)


if __name__ == "__main__":
    try:
        if op.exists("static/data"):
            os.unlink("static/data")
        if op.exists("static/analysis"):
            os.unlink("static/analysis")
        os.symlink(op.join(project["analysis_dir"], args.experiment),
                   "static/analysis")
        os.symlink(project["data_dir"], "static/data")
        app.run(debug=args.debug, port=args.port)
    finally:
        if op.exists("static/data"):
            os.unlink("static/data")
        if op.exists("static/analysis"):
            os.unlink("static/analysis")
