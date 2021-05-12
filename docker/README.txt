########################################
# Requirements
########################################

- Docker and Docker Compose

########################################
# Setup 
########################################

### Download repository from github

git clone https://github.com/eo2cube/namibia_workshop.git

### Navigate to docker folder

cd namibia_workshop/docker

### Spin up datacube environment

docker-compose up -d

Note: if you are not running as root, you may have to add your current user to the docker group

sudo groupadd docker

sudo usermod -aG docker $USER

##########################################
# Index environemnt
##########################################

### Enter index environment

docker exec -it dcindex /bin/bash


### Download sentinel data

sentinelsat --user <username>  --password <password> --url https://apihub.copernicus.eu/apihub --geometry /home/datacube/aoi/windhoek.geojson  --sentinel 2 --producttype S2MSI2A --start NOW-10DAY --path /home/datacube/example_data/ --download 


##########################################
# Jupyter
##########################################
 
### Access Jupyter
 
http://127.0.0.1:8082/

### Credentials

Username: <username>
Password: datacube
