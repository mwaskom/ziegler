Ziegler: fMRI Reporting Webapp
==============================

Ziegler is a lightweight [Flask](http://flask.pocoo.org/) based webapp for reporting the results of [lyman](https://github.com/mwaskom/lyman) analyses.

To view the results from your default experiment, run

    python ziegler.py

This starts the app at `http://localhost:5000`.

There are a few other options; run with `--help` to see them.

The lyman `data` and `analysis` directories are softlinked in `static/` when the app starts. This is cleaned up on exit, but you might not want to keep the ap in your Dropbox, as these large directories will be synced.

To view the app on a computer with no existing lyman environment, do

    export LYMAN_DIR=testing/lyman

You won't be able to generate any reports (there's no real data), but you can see what things look like and develop the basic interface.

Dependencies
------------
- [Flask](http://flask.pocoo.org/)
- [lyman](https://github.com/mwaskom/lyman)

To generate PDF reports, you'll also need to have [pandoc](http://johnmacfarlane.net/pandoc/) and pdflatex installed.

License
-------
Simplified BSD
