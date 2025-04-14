// src/storage.js
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs');
 
// Ensure data directory exists
const dataDir = path.join(process.env.HOME || process.env.USERPROFILE, '.rin');
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir);
}
 
const dbPath = path.join(dataDir, 'rin.db');
let db;
 
function init() {
  db = new sqlite3.Database(dbPath);
  
  // Create tables if they don't exist
  db.serialize(() => {
    db.run(`
      CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT,
        response TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);
  });
  
  console.log(`Local memory initialized at ${dbPath}`);
}
 
function saveInteraction(query, response) {
  return new Promise((resolve, reject) => {
    db.run(
      'INSERT INTO interactions (query, response) VALUES (?, ?)',
      [query, response],
      function(err) {
        if (err) return reject(err);
        resolve(this.lastID);
      }
    );
  });
}
 
function getInteractions(limit = 10) {
  return new Promise((resolve, reject) => {
    db.all(
      'SELECT * FROM interactions ORDER BY timestamp DESC LIMIT ?',
      [limit],
      (err, rows) => {
        if (err) return reject(err);
        resolve(rows);
      }
    );
  });
}
 
module.exports = { init, saveInteraction, getInteractions };