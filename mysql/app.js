var express = require('express');
const mysql = require('mysql2');
const env = require('dotenv').config({ path: "../.env" });

const app = express()

// MySQL 서버에 연결할 정보 설정
const connection = mysql.createConnection({
    host:process.env.host,
    user:process.env.user,
    port:process.env.port,
    password:process.env.password,
    database:process.env.database
});

  // MySQL 서버에 연결
connection.connect((err) => {
    if (err) {
        console.error('Error connecting to MySQL database:', err);
        return;
    }
    console.log('Connected to MySQL database!');
});

  // 새로운 테이블 생성 쿼리
const createTableQuery = `
    CREATE TABLE IF NOT EXISTS search (
        id INT AUTO_INCREMENT PRIMARY KEY,
        park VARCHAR(255) NOT NULL,
        cnt INT NOT NULL
    )
`;

// 테이블 생성
connection.query(createTableQuery, (err, results) => {
    if (err) {
        console.error('Error creating table:', err);
        return;
    }
    console.log('Search table created successfully!');
});

app.listen(8000, function() {
    console.log('8000 Port : Server Started~!!');
})