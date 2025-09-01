
DROP TABLE IF EXISTS verifications;

CREATE TABLE verifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  filename TEXT NOT NULL,
  verified_at TIMESTAMP NOT NULL,
  is_authentic BOOLEAN NOT NULL,
  result_message TEXT NOT NULL
);
