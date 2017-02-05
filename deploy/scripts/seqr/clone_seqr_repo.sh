set -x

git clone -q https://github.com/macarthur-lab/seqr;

cd seqr; git checkout feature-refactor_ui_to_use_react.js;

# init local config files
cp deploy/example_config_files/*.py .
