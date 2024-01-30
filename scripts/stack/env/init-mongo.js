// Create a new database and switch to it
db = db.getSiblingDB('$COSIM_DB');

// Create a new collection and insert documents
db.scenarios.insert([
  { "collection name": 'scenarios' },
]);

db.federations.insert([
  { "collection name": 'federations' },
]);

// Create a user with read and write privileges for the database
db.createUser({
  user: '$COSIM_USER',
  pwd: '$COSIM_PASSWORD',
  roles: [
    { role: 'readWrite', db: '$COSIM_DB' }
  ]
});
