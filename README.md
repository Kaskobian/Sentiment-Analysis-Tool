# sentiment-analysis

Install Dependencies:
1. Ensure Ubuntu version 24.04 LTS ("Noble"), 22.04 LTS ("Jammy"), or 20.04 LTS ("Focal")
2. Install MongoDB 8.0 community version by following instructions https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/
3. sudo apt update
4. sudo apt install nodejs
5. sudo apt install npm
6. sudo apt install python3 (if not already)
7. sudo apt install python3.10-venv

Steps to setup dev environment 
1. cd /scripts
2. chmod +x create_env.sh
3. ./create_env.sh 
4. wait a long time
5. copy model file from https://drive.google.com/file/d/1W6NMfj0IK4477x-6QSKY9ApWTMGBMJwg/view?usp=sharing to /backend/classify/sentiment_model

Steps to run:
1. cd /scripts
2. chmod +x run_backend.sh
3. chmod +x run_frontend.sh
4. ./run_backend.sh
5. ./run_frontend.sh (different terminal)
6. open http://localhost:3000/
