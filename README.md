Ziegler: fMRI Reporting Webapp
==============================

Ziegler is a lightweight [Flask](http://flask.pocoo.org/) based webapp for reporting the results of [lyman](https://github.com/mwaskom/lyman) analyses.

To view the results from your default experiment, run

    python ziegler.py

This starts the app at `http://localhost:5000`.

There are a few other options; run with `--help` to see them.

At the moment, the lyman `data/` and `analysis/` directories are softlinked in `static/` when the app starts. This is cleaned up on exit, but you might not want to keep the app in your Dropbox, as these large directories will be synced.

Dependencies
------------
- [Flask](http://flask.pocoo.org/)
- [lyman](https://github.com/mwaskom/lyman)

License
-------
Simplified BSD
