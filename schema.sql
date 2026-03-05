CREATE TABLE IF NOT EXISTS households (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  invite_code TEXT NOT NULL UNIQUE,
  created_on DATETIME DEFAULT CURRENT_TIMESTAMP,
  created_by INTEGER NOT NULL,
  FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('parent','kid')),
    household_id INTEGER,
    created_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(household_id) REFERENCES households(id)
);

CREATE TABLE IF NOT EXISTS chore_templates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  points INTEGER NOT NULL DEFAULT 1,
  active TEXT NOT NULL DEFAULT 'Y' CHECK(active IN ('Y','N')),
  created_on DATETIME DEFAULT CURRENT_TIMESTAMP,
  created_by INTEGER NOT NULL,
  FOREIGN KEY(household_id) REFERENCES households(id),
  FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS chore_submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  template_id INTEGER NOT NULL,
  kid_id INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'submitted' CHECK(status IN ('submitted','approved','denied')),
  note TEXT,
  points_earned INTEGER,
  submitted_on DATETIME DEFAULT CURRENT_TIMESTAMP,
  reviewed_on DATETIME,
  reviewed_by INTEGER,
  FOREIGN KEY(template_id) REFERENCES chore_templates(id),
  FOREIGN KEY(kid_id) REFERENCES users(id),
  FOREIGN KEY(reviewed_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS prize_templates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  points_cost INTEGER NOT NULL CHECK(points_cost > 0),
  active TEXT NOT NULL DEFAULT 'Y' CHECK(active IN ('Y','N')),
  created_on DATETIME DEFAULT CURRENT_TIMESTAMP,
  created_by INTEGER NOT NULL,
  FOREIGN KEY(household_id) REFERENCES households(id),
  FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS prize_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  template_id INTEGER NOT NULL,
  kid_id INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'requested'
    CHECK(status IN ('requested','approved','denied','fulfilled')),
  note TEXT,
  points_cost INTEGER NOT NULL,
  requested_on DATETIME DEFAULT CURRENT_TIMESTAMP,
  reviewed_on DATETIME,
  reviewed_by INTEGER,
  fulfilled_on DATETIME,
  FOREIGN KEY(template_id) REFERENCES prize_templates(id),
  FOREIGN KEY(kid_id) REFERENCES users(id),
  FOREIGN KEY(reviewed_by) REFERENCES users(id)
);