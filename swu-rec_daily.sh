cd ~/swu-rec

# Fetch swu-rec-backend
git fetch --all
git reset --hard origin/main

# Fetch swu-rec (HTML)
cd html
git fetch --all
git reset --hard origin/main
cd ..

# Run program
. ../.swu-rec/bin/activate
python3 main.py

# Commit swu-rec-backend
git add .
git commit -m "Daily Update"
git push origin

# Commit swu-rec (HTML)
cd html
git add .
git commit -m "Daily Update"
git push origin
