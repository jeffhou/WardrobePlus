from flask import Flask, render_template, redirect, url_for, request
app = Flask(__name__)

clothes = []
clothes_guid = 0

companions = []
companion_guid = 0

class Companion:
    guid_counter = 0
    def __init__(self):
        self.guid = Companion.guid_counter
        self.paired = False
        Companion.guid_counter += 1

class Clothing:
    def __init__(self, name):
        self.name = str(name)
        self.companion = None
        self.compatible_clothes = []
    def pair(self, other):
        self.compatible_clothes.append(other)
    def addCompanion(self, comp):
        self.companion = comp
        self.companion.paired = True
    def removeCompanion(self):
        self.companion.paired = False
        self.companion = None
    def getCompanion(self):
        return self.companion
    def hasCompanion(self):
        return self.companion != None

@app.route('/')
def index():
    return render_template('landing_menu.html')

@app.route('/edit_wardrobe')
def edit_wardrobe():
    global clothes, companions
    return render_template('edit_wardrobe.html', clothes=clothes, companions=companions)

@app.route('/begin_session')
def begin_session():
    return 'BEGIN SESSION'

@app.route('/add_clothing')
def add_clothing():
    global clothes_guid, clothes
    return render_template('new_clothing.html', companions=companions)
    #return redirect(url_for("edit_wardrobe"))

@app.route('/add_companion')
def add_companion():
    global companions, companion_guid
    companions.append(Companion())
    return redirect(url_for("edit_wardrobe"))

@app.route('/new_clothing', methods=['POST'])
def new_clothing():
    companion_guid = int(request.form['companion_guid'])
    companion = None
    if companion_guid == -1:
        companion = Companion()
        companions.append(companion)
    else:
        print companions
        print companion_guid
        for i in companions:
            print "i.guid", type(i.guid)
            print "companion_guid", type(companion_guid)
            print i.guid == companion_guid
            if i.guid == companion_guid:
                companion = i
        if companion == None:
            raise Exception
    clothing_name = request.form['name']
    new_clothing = Clothing(clothing_name)
    clothes.append(new_clothing)
    new_clothing.addCompanion(companion)
    return redirect(url_for("edit_wardrobe"))
if __name__ == '__main__':
    app.run('0.0.0.0', debug=True)
