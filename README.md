fMRI Reporting Webapp
=====================

Ziegler is a lightweight Flask-based webapp for reporting the results of [lyman](https://github.com/mwaskom/lyman) analyses.

To view the results from your default experiment, run

    python ziegler.py

Which will start the app in `localhost:5000`

At the moment, the lyman data/ and analysis/ directories get softlinked in static/ when the app starts. This gets cleaned up on exit, but you might not want to keep the app in a Dropbox or similar folder, as it will try to sync what can be very large directories.

Dependencies
------------
- [Flask](http://flask.pocoo.org/)
- [lyman](https://github.com/mwaskom/lyman)

License
-------
Simplified BSD
