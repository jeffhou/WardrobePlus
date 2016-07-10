from flask import Flask, render_template, redirect, url_for, request
app = Flask(__name__)

clothes = []
clothes_guid = 0
def getClothing(guid):
    global clothes    
    for i in clothes:
        if guid == i.guid:
            return i

companions = []
companion_guid = 0
def getCompanion(guid):
    global companions    
    for i in companions:
        if guid == i.guid:
            return i

class Companion:
    guid_counter = 0
    def __init__(self):
        self.guid = Companion.guid_counter
        self.paired = False
        Companion.guid_counter += 1

class Clothing:
    guid_counter = 0
    def __init__(self, name):
        self.name = str(name)
        self.companion = None
        self.compatible_clothes = []
        self.guid = Clothing.guid_counter
        Clothing.guid_counter += 1
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
    return redirect(url_for("sessionCheckout"))

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

@app.route('/add_sample_set')
def add_sample_set():
    colors = ["Coral", "Black", "White", "Pink", "Blue", "Canary"]
    styles = ["Shirt", "Pants", "OCBD", "Jacket", "Tie", "Hat"]
    samples = []
    for i in colors:
        for j in styles:
            samples.append(i + " " + j)

    for i in samples:
        companion = Companion()
        companions.append(companion)
        clothing = Clothing(i)
        clothes.append(clothing)
        clothing.addCompanion(companion)
    return redirect(url_for("edit_wardrobe"))

@app.route('/session#checkout')
def sessionCheckout():
    global clothes
    if 'clothingGUID' in request.args:
        clothingGUID = int(request.args['clothingGUID'])
        #todo: extract getclothingbyguid
        for i in clothes:
            if clothingGUID == i.guid:
                i.removeCompanion()
    return render_template('session.html', clothes=clothes)

@app.route('/session#return')
def sessionReturn():
    global clothes, companions
    
    if 'clothingGUID' in request.args:
        clothingGUID = int(request.args['clothingGUID'])
        #todo: extract getclothingbyguid
        for i in clothes:
            if clothingGUID == i.guid:
                return render_template('return_clothing.html', clothing=i, companions=companions)
    return render_template('session.html', clothes=clothes)

@app.route('/session#returned', methods=['GET', 'POST'])
def sessionReturned():
    global clothes
    print "@@@@@@@@@@@@@@@@@@"
    companion_guid = int(request.form['companion_guid'])
    clothing_guid = int(request.args['clothing_guid'])
    print "##################"
    companion = getCompanion(companion_guid)
    clothing = getClothing(clothing_guid)
    clothing.addCompanion(companion)
    return redirect(url_for('sessionCheckout'))

if __name__ == '__main__':
    app.run('0.0.0.0', debug=True, port=8080)
