Ziegler: fMRI Reporting Webapp
==============================

Ziegler is a lightweight [Flask](http://flask.pocoo.org/) based webapp for reporting the results of [lyman](https://github.com/mwaskom/lyman) analyses.

To view the results from your default experiment, run

    python ziegler.py

This starts the app at `http://localhost:5000`.

There are a few other options; run with `--help` to see them.

At the moment, the lyman `data/` and `analysis/` directories are softlinked in `static/` when the app starts. This is cleaned up on exit, but you might not want to keep the app in your Dropbox, as these large directories will be synced.

In addition to the report generation form, you can also create reports by specifying a url. To generate a full report for a given subject, point your browser to

    http://{app address}/<subj>/<space>

The mni space is used by default if it is missing. You can also create a report for a group analysis in this way. To show all group contrasts, use

    http://{app address}/group

but you can also show a specific contrast with

    http://{app address}/group/<contrast>

To view the app on a computer with no existing lyman environment, do

    export LYMAN_DIR=testing/lyman

You won't be able to generate any reports (there's no real data), but you can see what
things look like and develop the basic interface.

Dependencies
------------
- [Flask](http://flask.pocoo.org/)
- [lyman](https://github.com/mwaskom/lyman)

License
-------
Simplified BSD
