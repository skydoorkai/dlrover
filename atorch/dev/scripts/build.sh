set -e
python tools/scripts/render_setup.py --version 0.0.1
python setup.py bdist_wheel
