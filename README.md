Install Dependencies:

Ensure Ubuntu version 24.04 LTS ("Noble"), 22.04 LTS ("Jammy"), or 20.04 LTS ("Focal")
Install MongoDB 8.0 community version by following instructions https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/
sudo apt update
sudo apt install nodejs
sudo apt install npm
sudo apt install python3 (if not already)
sudo apt install python3.10-venv
Steps to setup dev environment

cd /scripts
chmod +x create_env.sh
./create_env.sh
wait a long time
copy model file from https://drive.google.com/file/d/1W6NMfj0IK4477x-6QSKY9ApWTMGBMJwg/view?usp=sharing to /backend/classify/sentiment_model
Steps to run:

cd /scripts
chmod +x run_backend.sh
chmod +x run_frontend.sh
./run_backend.sh
./run_frontend.sh (different terminal)
open http://localhost:3000/
