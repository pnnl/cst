// Create a new database and switch to it
db = db.getSiblingDB('$CST_DB');

// Create a new collection and insert documents
db.scenarios.insert([
  { "collection name": 'scenarios' },
]);

db.federations.insert([
  { "collection name": 'federations' },
]);

// Create a user with read and write privileges for the database
db.createUser({
  user: '$CST_USER',
  pwd: '$CST_PASSWORD',
  roles: [
    { role: 'readWrite', db: '$CST_DB' }
  ]
});
