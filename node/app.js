const express = require('express')
const morgan =  require('morgan') //서버 로그를 남겨줌
const path = require('path')
const app = express()
const bodyParser = require('body-parser')
const cookieParser = require('cookie-parser')
const axios = require('axios');
const cors = require('cors');


app.set('port',  8000);
app.use(morgan('dev'));
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: false }));
app.use(cookieParser());
app.use(express.static(path.join(__dirname, 'public')))
app.use(cors());

var main = require('./routes/main')
app.use('/', main)

app.listen(app.get('port'), () => {
    console.log('8000 Port : Server Started~!!')
})