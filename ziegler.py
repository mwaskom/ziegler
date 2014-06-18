import os
import sys
import os.path as op
import json
import pprint
from glob import glob
import argparse
import subprocess as sp
import pandas as pd

from flask import (Flask, request, render_template,
                   redirect, send_file)

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

subjects = lyman.determine_subjects(args.subjects)
exp_base = args.experiment

app = Flask(__name__)


def basic_info(experiment=exp_base):
    """Basic information needed before any report options are set."""
    experiments = list_experiments()
    exp = experiment_info(experiment)

    subjects_size = min(len(subjects), 10)

    runs = range(1, exp["n_runs"] + 1)

    contrasts = exp["contrast_names"]
    contrast_size = len(contrasts)

    anal_root = op.join("static", exp_base, "analysis", experiment)
    data_root = op.join("static", exp_base, "data")

    all_rois = glob(data_root + "/*/masks/*.png")
    all_rois = [op.splitext(op.basename(m))[0] for m in all_rois]
    all_rois = sorted(list(set(all_rois)))
    roi_size = min(len(all_rois), 10)

    group_names = glob(anal_root + "/*/mni") + glob(anal_root + "/*/fsaverage")
    group_names = [p.split("/")[-2] for p in group_names]
    group_names = sorted(list(set(group_names)))
    group_size = min(len(group_names), 10)

    any_anatomy = (bool(glob(data_root + "/*/snapshots")) or
                   bool(glob(data_root + "/*/normalization")))
    any_preproc = bool(glob(anal_root + "/*/preproc"))
    any_model = bool(glob(anal_root + "/*/model"))
    any_ffx = bool(glob(anal_root + "/*/ffx"))
    any_rois = bool(all_rois)
    any_group = bool(group_names)
    any_contrasts = any_model or any_ffx or any_group

    hemis = ["lh", "rh"]

    return dict(all_subjects=subjects,
                subjects_size=subjects_size,
                exp_base=exp_base,
                experiment=experiment,
                experiments=experiments,
                runs=runs,
                hemis=hemis,
                all_contrasts=contrasts,
                contrast_size=contrast_size,
                all_rois=all_rois,
                roi_size=roi_size,
                group_names=group_names,
                group_size=group_size,
                any_anatomy=any_anatomy,
                any_preproc=any_preproc,
                any_model=any_model,
                any_ffx=any_ffx,
                any_rois=any_rois,
                any_group=any_group,
                any_contrasts=any_contrasts,
                )


def list_experiments():

    lyman_dir = os.environ["LYMAN_DIR"]
    experiments = glob(op.join(lyman_dir, exp_base + "-*.py"))
    experiments.append(exp_base)
    return sorted(op.splitext(op.basename(e))[0] for e in experiments)


def experiment_info(experiment):

    parts = experiment.split("-")
    try:
        exp_base, altmodel = parts
    except ValueError:
        exp_base, = parts
        altmodel = None

    info = lyman.gather_experiment_info(exp_base, altmodel)
    return info


@app.route("/")
def redirect_to_experiment_base():
    return redirect(exp_base)


@app.route("/<experiment>")
def home(experiment):
    """Build the selector column."""
    info = basic_info(experiment)
    return render_template("layout.html", **info)


@app.route("/<experiment>/report", methods=["GET", "POST"])
def generate_report(experiment):
    """Build the main report."""
    info = basic_info(experiment)
    info["report"] = True

    if request.method == "POST":
        form = request.form
    elif request.method == "GET":
        form = request.args

    # Generate a url for the report
    # This cannot be the right way to do this
    args = ""
    hasgroup = form.getlist("maps") or form.getlist("peaks")
    for key in form:
        if key == "btn":
            continue
        elif key == "multiselect":
            continue
        elif key == "ffxspace" and not form.getlist("ffx"):
            continue
        elif key == "groupspace" and not hasgroup:
            continue
        elif key == "groupname" and not hasgroup:
            continue
        elif key == "contrasts" and not (form.getlist("model")
                                         or form.getlist("ffx")
                                         or hasgroup):
            continue
        for value in form.getlist(key):
            args += "%s=%s&" % (key, value)
    url = request.url + "?" + args
    info["report_url"] = unicode(url)

    # Populate the info dict
    info = request_to_info(form, info)

    # Possibly generate a PDF
    if form.get("pdf", "no") == "yes":
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


@app.route("/<experiment>/viewer")
def viewer(experiment):
    info = basic_info(experiment)
    info["papaya"] = True

    info["anat"] = request.args.get("anat")
    info["anat_name"] = os.path.basename(info["anat"])
    info["anat_max"] = request.args.get("anat_max", 100)
    info["overlay"] = request.args.get("overlay")
    info["overlay_name"] = os.path.basename(info["overlay"])
    info["min"] = request.args.get("min", 2)
    info["max"] = request.args.get("max", 6)
    info["lut"] = request.args.get("lut", "Reds")
    info["negative_lut"] = request.args.get("negative_lut", "Blues")
    info["parametric"] = request.args.get("parametric", "false")

    info["name"] = request.args.get("name")
    info["contrast"] = request.args.get("contrast")

    return render_template("viewer.html", **info)


@app.route("/<experiment>/experiment")
def experiment(experiment):
    info = basic_info(experiment)
    exp_string = pprint.pformat(experiment_info(experiment))
    return render_template("experiment.html",
                           experiment_parameters=exp_string,
                           **info)


@app.template_filter("render_exp_json")
def render_exp_json(json_file):
    with open(json_file[1:]) as fid:
        params = json.load(fid)
        params = pprint.pformat(params)
        return r"<pre><code>{}</code></pre><br>".format(params)


@app.template_filter("csv_to_html")
def cluster_csv_to_html(csv_file):
    """Read the csv file with peak information and generate an html table."""
    try:
        df = pd.read_csv(str(csv_file)[1:], index_col="Peak")
    except IOError:
        return "<p>Could not read %s </p><br>" % csv_file

    if not len(df):
        return "<p>No significant clusters</p><br>"

    df = df.reset_index()
    df["Peak"] += 1
    df["Prob"] = df["Prob"].astype(int)
    html = df.to_html(index=False, classes=["table",
                                            "table-striped",
                                            "table-condensed"])
    html = html.replace('border="1"', '')
    html = html.replace('class="dataframe ', 'class="')
    return html


@app.template_filter("corrected_mni_viewer")
def corrected_mni_viewer(contrast, experiment, groupname):

    link = "&".join([
        "lut=OrRd",
        "anat=/static/data/MNI152.nii.gz", "anat_max=9000",
        "name=" + groupname, "contrast=" + contrast,
        "overlay=/static/"
        "{0}/analysis/{1}/{2}/mni/{3}/zstat1_threshold.nii.gz".format(
            exp_base, experiment, groupname, contrast)])
    return "viewer?" + link


@app.template_filter("uncorrected_mni_viewer")
def uncorrected_mni_viewer(contrast, experiment, groupname):

    link = "&".join([
        "lut=warm",
        "negative_lut=cool",
        "anat=/static/data/MNI152.nii.gz", "anat_max=9000",
        "name=" + groupname, "contrast=" + contrast,
        "min=1.7",
        "max=4",
        "parametric=true",
        "overlay=/static/"
        "{0}/analysis/{1}/{2}/mni/{3}/zstat1.nii.gz".format(
            exp_base, experiment, groupname, contrast)])
    return "viewer?" + link


@app.template_filter("subject_zstat_viewer")
def subject_zstat_viewer(contrast, experiment, subj, space):

    if space == "mni":
        anat = ("/static/{0}/data/{1}/normalization/brain_warp.nii.gz"
                .format(exp_base, subj))
        anat_max = "110"
    else:
        anat = ("/static/{0}/analysis/{1}/{2}/preproc/run_1/mean_func.nii.gz"
                .format(exp_base, experiment, subj))
        anat_max = "2500"

    link = "&".join([
        "lut=OrRd", "negative_lut=PuBu", "max=12", "parametric=true",
        "anat=" + anat, "anat_max=" + anat_max,
        "name=" + subj, "contrast=" + contrast,
        "overlay=/static/"
        "{0}/analysis/{1}/{2}/ffx/{3}/smoothed/{4}/zstat1.nii.gz".format(
            exp_base, experiment, subj, space, contrast)])
    return "viewer?" + link


@app.template_filter("thresh_pos")
def thresh_pos(palette):
    return 0 if palette == "grayscale" else 2.3


@app.template_filter("thresh_neg")
def thresh_neg(palette):
    return 0 if palette == "grayscale" else -2.3


def request_to_info(req, info):
    """Given a request multidict, populate the info dict."""
    keys = ["subjects", "anatomy", "preproc", "model", "ffx",
            "rois", "maps", "peaks", "params", "contrasts"]
    for key in keys:
        info[key] = req.getlist(key)
    info["ffxspace"] = req.get("ffxspace", "")
    info["groupspace"] = req.get("groupspace", "")
    groupname = req.get("groupname", "group")
    info["groupname"] = groupname if groupname else "group"

    return info


def link_source():
    """Link source directories to static/."""
    unlink_source()
    os.mkdir("static/" + exp_base)
    os.symlink(op.join(project["analysis_dir"]),
               "static/%s/analysis" % exp_base)
    os.symlink(project["data_dir"], "static/%s/data" % exp_base)


def unlink_source():
    """Remove source directories from static/, if they exist."""
    root = "static/" + exp_base
    if op.exists(root):
        for sub_dir in ["data", "analysis"]:
            path = "%s/%s" % (root, sub_dir)
            if op.exists(path):
                os.unlink(path)
        os.rmdir(root)


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
