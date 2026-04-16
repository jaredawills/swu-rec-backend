git fetch --all
git reset --hard origin/main
source ../.swu-rec/bin/activate
python3 main.py
git add .
git commit -m "Daily Update"
git push origin
cd html
git add .
git commit -m "Daily Update"
git push origin
git fetch --all
git reset --hard origin/main
source ../.swu-rec/bin/activate
python3 main.py
git add .
git commit -m "Daily Update"
git push origin
cd html
git add .
git commit -m "Daily Update"
git push origin
