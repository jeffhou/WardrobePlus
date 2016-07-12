from flask import Flask, render_template, redirect, url_for, request
app = Flask(__name__)


clothes = []
clothes_guid = 0
def getClothing(guid):
    global clothes    
    for i in clothes:
        if guid == i.guid:
            return i

class Clothing:
    guid_counter = 0
    def __init__(self, name):
        self.name = str(name)
        self.compatible_clothes = []
        self.guid = Clothing.guid_counter
        self.inWardrobe = True
        Clothing.guid_counter += 1
    def pair(self, other):
        self.compatible_clothes.append(other)
    def isInWardrobe(self):
        return self.inWardrobe

@app.route('/')
def index():
    return render_template('landing_menu.html')

@app.route('/edit_wardrobe')
def edit_wardrobe():
    global clothes
    return render_template('edit_wardrobe.html', clothes=clothes)

@app.route('/begin_session')
def begin_session():
    return redirect(url_for("sessionCheckout"))

@app.route('/add_clothing')
def add_clothing():
    global clothes_guid, clothes
    return render_template('new_clothing.html')
   

@app.route('/new_clothing', methods=['POST'])
def new_clothing():
    clothing_name = request.form['name']
    new_clothing = Clothing(clothing_name)
    clothes.append(new_clothing)
    return redirect(url_for("edit_wardrobe"))

@app.route('/remove_clothing', methods=['GET', 'POST']) 
def remove_clothing():
    global clothes_guid, clothes
    return render_template('delete_clothing.html', clothes=clothes)
   

@app.route('/delete_clothing', methods=['GET', 'POST'])
def delete_clothing(): 
   
    select = request.form.get('comp_select') #this is now working
    
    select = int(select)

    clothes.remove(getClothing(select))
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
        clothing = Clothing(i)
        clothes.append(clothing)
    return redirect(url_for("edit_wardrobe"))

@app.route('/session#checkout')
def sessionCheckout():
    global clothes
    if 'clothingGUID' in request.args:
        clothingGUID = int(request.args['clothingGUID'])
        #todo: extract getclothingbyguid
        for i in clothes:
            if clothingGUID == i.guid:
                i.inWardrobe = False
    return render_template('session.html', clothes=clothes)

@app.route('/session#return')
def sessionReturn():
    global clothes
    if 'clothingGUID' in request.args:
        clothingGUID = int(request.args['clothingGUID'])
        #todo: extract getclothingbyguid
        for i in clothes:
            if clothingGUID == i.guid:
                i.inWardrobe = True 
    return render_template('session.html', clothes=clothes)

if __name__ == '__main__':
    app.run('0.0.0.0', debug=True, port=8080)

