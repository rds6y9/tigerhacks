CREATE TABLE users (
	id                int                 PRIMARY KEY AUTO_INCREMENT,
	display_name      VARCHAR(200),
	graph_id					VARCHAR(100),
	email							VARCHAR(200)
);


CREATE TABLE friends (
	uid1			  int,
	uid2			  int,
	PRIMARY KEY (uid1, uid2),
	FOREIGN KEY (uid1) REFERENCES users(id),
	FOREIGN KEY (uid2) REFERENCES users(id)
);

CREATE TABLE articles (
	id				int			PRIMARY KEY AUTO_INCREMENT,
	url				VARCHAR(500),
	rating			int,
	post_date		date,
	tag         int,
	CONSTRAINT Check_rating_range CHECK (rating >= 0 AND rating <= 5)
);

CREATE TABLE userboards (
	uid 			  int,
	aid				  int,
	PRIMARY KEY (uid, aid),
	FOREIGN KEY (uid) REFERENCES users(id),
	FOREIGN KEY (aid) REFERENCES articles(id)
);

CREATE TABLE catboards (
	id				int			PRIMARY KEY AUTO_INCREMENT,
	name			VARCHAR(100),
	uid				int,
	FOREIGN KEY (uid) REFERENCES users(id)
);

CREATE TABLE subscriptions (
	uid			int,
	bid			int,
	FOREIGN KEY (uid) REFERENCES users(id),
	FOREIGN KEY (bid) REFERENCES catboards(id)
);

CREATE TABLE catarticles (
	bid			int,
	aid			int,
	FOREIGN KEY (bid) REFERENCES catboards(id),
	FOREIGN KEY (aid) REFERENCES articles(id)
);
