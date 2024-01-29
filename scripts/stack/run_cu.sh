#docker run -it --rm cosim-python bash
#docker exec -it c4538d7c2d71 bash


docker run -d \
  --name mymongodb \
  -e MONGO_INITDB_DATABASE=copper \
  -e MONGO_INITDB_ROOT_USERNAME=root \
  -e MONGO_INITDB_ROOT_PASSWORD=rootpassword \
  -v ./init-mongo.js:/docker-entrypoint-initdb.d/init-mongo.js:ro \
  mongodb/mongodb-community-server