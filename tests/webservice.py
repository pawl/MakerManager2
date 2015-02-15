from flask import Flask, request
app = Flask(__name__)


@app.route("/")
def index():
    ''' Test version of the webservice for:
        https://github.com/pawl/Chinese-RFID-Access-Control-Library
    '''
    
    apiKey = request.args.get('apiKey')
    action = request.args.get('action')
    badge = request.args.get('badge')
    
    if (apiKey == "secret"):
        if badge:
            if (action == "remove"):
                return "User Removed Successfully"
            elif (action == "add"):
                return "User Added Successfully"
            else:
                return "must specify an action"
        else:
            return "no badge number entered"
    else:
        return "" #return nothing when no API key is entered


if __name__ == "__main__":
    app.run(port=5050, debug=True)