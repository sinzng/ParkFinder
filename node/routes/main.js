const express = require('express')
const bodyParser = require('body-parser')
const XMLHttpRequest = require("xhr2");
const cors = require('cors');
const app = express()
const router = express.Router();

app.use(bodyParser.json())
app.use(bodyParser.urlencoded({ extended: false }))
app.use(express.json())
app.use(express.urlencoded({ extended:true }))

// get all parks
app.get('/parks', async (req, res ) => {
    const location = req.query.location; // 클라이언트에서 보낸 위치 정보

    const xhr = new XMLHttpRequest();
    xhr.open("GET", `http://0.0.0.0:3000/parks?location=${encodeURIComponent(location)}`);
    xhr.setRequestHeader("content-type", "application/json");
    xhr.send();

    xhr.onload = () => {
        if (xhr.status === 200) {
            const responseData = JSON.parse(xhr.responseText);
            console.log(responseData);
            res.json(responseData); // 클라이언트로 데이터를 응답
        } else {
            console.error(xhr.status, xhr.statusText);
            res.status(500).json({ error: 'Failed to fetch nearest parks' });
        }
    };
});

// get near parks
app.get('/nearparks', async (req, res ) => {
    const location = req.query.location; // 클라이언트에서 보낸 위치 정보

    const xhr = new XMLHttpRequest();
    xhr.open("GET", `http://0.0.0.0:3000/nearparks?location=${encodeURIComponent(location)}`);
    xhr.setRequestHeader("content-type", "application/json");
    xhr.send();

    xhr.onload = () => {
        if (xhr.status === 200) {
            const responseData = JSON.parse(xhr.responseText);
            console.log(responseData);
            res.json(responseData); // 클라이언트로 데이터를 응답
        } else {
            console.error(xhr.status, xhr.statusText);
            res.status(500).json({ error: 'Failed to fetch nearest parks' });
        }
    };
});

// get all parks
app.get('/getratio', async (req, res ) => {
    const location = req.query.location; // 클라이언트에서 보낸 위치 정보

    const xhr = new XMLHttpRequest();
    xhr.open("GET", `http://0.0.0.0:3000/getratio?region=${encodeURIComponent(location)}`);
    xhr.setRequestHeader("content-type", "application/json");
    xhr.send();

    xhr.onload = () => {
        if (xhr.status === 200) {
            const responseData = JSON.parse(xhr.responseText);
            console.log(responseData);
            res.json(responseData); // 클라이언트로 데이터를 응답
        } else {
            console.error(xhr.status, xhr.statusText);
            res.status(500).json({ error: 'Failed to fetch nearest parks' });
        }
    };
});
// get create chart
axios

module.exports = app;