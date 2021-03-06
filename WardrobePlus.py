# Documentation seen in this file was created based on recommendations from
# http://docs.python-guide.org/en/latest/writing/documentation/

from flask import Flask, render_template, redirect, url_for, request, g, session
from functools import wraps
import inspect, os, requests, json
from WardrobeDB import WardrobeDB

app = Flask(__name__)
APP_ID = os.environ.get("app_id", "1749612118637213")
APP_SECRET = os.environ.get("app_secret", "194cf8a3575a0f27e695a876b3288a24")

def getDB():
  if not hasattr(g, 'sqlite_db'):
    g.sqlite_db = WardrobeDB()
    user = getSessionTokenStatus()["user"]
    g.sqlite_db.setUser(user)
  return g.sqlite_db

@app.teardown_appcontext
def closeDB(error):
  if hasattr(g, 'sqlite_db'):
    g.sqlite_db.closeDB()

def getClothes(sort_=False):
  clothes = getDB().getClothesDB()
  clothesList = []
  for i in clothes:
    clothName = str(i[1])
    clothTags = getDB().getTagsByClothId(int(i[0])) #TODO need to recast/retype this variable
    clothInWardrobe = bool(i[2])
    clothGuid = int(i[0])
    clothUsage = {}
    clothUsage["week"] = getDB().getUsage(clothGuid, 7)
    clothUsage["month"] = getDB().getUsage(clothGuid, 30)
    clothUsage["threemonths"] = getDB().getUsage(clothGuid, 90)
    clothUsage["year"] = getDB().getUsage(clothGuid, 365)
    clothUsage["alltime"] = getDB().getUsage(clothGuid)
    clothesList.append(Clothing(clothName, clothTags, clothInWardrobe, clothGuid, clothUsage))

  if sort_:
    compatibilityScores = getCompatibilityScores()
    clothesList = sorted(clothesList, key=lambda x: compatibilityScores[x.guid], reverse=True)
  return clothesList

def getClothing(guid):
  for i in getClothes():
    if guid == i.guid:
      return i

class Clothing:

  def __init__(self, name, tags=[], inWardrobe=True, guid=-1, usage={}):
    self.name = str(name)
    self.guid = guid
    self.tags = tags
    self.inWardrobe = inWardrobe
    self.usage = usage

  def isInWardrobe(self):
    return self.inWardrobe

  def checkin(self):
    self.inWardrobe = True
    getDB().updateClothStatus(self.guid, 1)

  def checkout(self):
    self.inWardrobe = False
    getDB().updateClothStatus(self.guid, 0)

  def __str__(self):
    return "[Clothing]" + str({"name": self.name, "guid": self.guid,
        "tags": self.tags, "inWardrobe": self.inWardrobe})

def incrementCompatibility(clothId1, clothId2):
  clothId1, clothId2 = sorted((clothId1, clothId2))
  compatibility = getDB().executeDBCode("SELECT * FROM ClothCompatibilityUsage WHERE ClothId1 = %s AND ClothId2 = %s LIMIT 1" % (clothId1, clothId2), True)
  if len(compatibility) > 0:
    getDB().executeDBCode("UPDATE ClothCompatibilityUsage SET Usage = Usage + 1 WHERE ClothId1 = %s AND ClothId2 = %s" % (clothId1, clothId2))
  else:
    getDB().insert("ClothCompatibilityUsage", ("ClothId1", "ClothId2"), (clothId1, clothId2))

def getCompatibilityScores():
  compatibilityScores = {}
  for i in getDB().getClothesDB():
    i1 = i[0]
    if i[2] > 0:
      compatibilityScore = 0
      for j in getDB().getClothesDB():
        j1 = j[0]
        if not j[2] > 0:
          clothId1, clothId2 = sorted((i1, j1))
          clothingCompatibility = getDB().executeDBCode("SELECT * FROM ClothCompatibilityUsage WHERE ClothId1 = %s AND ClothId2 = %s LIMIT 1" % (clothId1, clothId2), True)
          if len(clothingCompatibility) > 0:
            compatibilityScore += clothingCompatibility[0][3]
      compatibilityScores[i1] = compatibilityScore
    else:
      compatibilityScores[i1] = 0
  return compatibilityScores

def incrementAllCompatibility():
  clothesIds = [i[0] for i in getDB().getClothsByStatus(False)]
  if len(clothesIds) > 1:
    for i in range(len(clothesIds)):
      for j in range(i + 1, len(clothesIds)):
        incrementCompatibility(clothesIds[i], clothesIds[j])

def incrementAllUsageStats():
  clothesIds = [i[0] for i in getDB().getClothsByStatus(False)]
  for i in clothesIds:
    getDB().incrementUsage(i)

def req_auth(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
    sessionTokenStatus = getSessionTokenStatus()
    if not sessionTokenStatus["valid"]:
      return render_template("auth_needed.html")
    return f(*args, **kwargs)
  return decorated_function

@app.route('/')
@req_auth
def index():
  getDB().createTables()
  return render_template('landing_menu.html', name=getCurrentUserFirstName())

@app.route('/save_changes')
@req_auth
def save_changes():
  incrementAllCompatibility()
  incrementAllUsageStats()
  return redirect(url_for('edit_wardrobe'))

@app.route('/return_all')
@req_auth
def return_all():
  getDB().updateAllClothesStatus(1)
  return redirect(url_for('use_wardrobe'))

@app.route('/clear_wardrobe')
@req_auth
def clear_wardrobe():
  getDB().createTables(True)
  return redirect(url_for('edit_wardrobe'))

@app.route('/edit_wardrobe', methods=['GET'])
@req_auth
def edit_wardrobe():
  clothes = getClothes()
  if 'search' in request.args:
    clothGuids = getDB().searchClothing(request.args['search'])
    clothes = filter(lambda x: x.guid in clothGuids, clothes)
  getDB().createTables()
  if 'tag' in request.args: #TODO show "no clothes match search parameters"
    tags = [int(request.args['tag'])]
    if 'selectedTags' in request.args:
      selectedTags = [int(i) for i in request.args.getlist('selectedTags')]
      tags += selectedTags
    return redirect(url_for('edit_wardrobe', selectedTags=tags))
  elif 'untag' in request.args:
    selectedTags = [int(i) for i in request.args.getlist('selectedTags')]
    selectedTags.remove(int(request.args['untag']))
    tags = selectedTags
    if len(selectedTags) > 0:
      return redirect(url_for('edit_wardrobe', selectedTags=selectedTags))
    else:
      return redirect(url_for('edit_wardrobe'))
  elif 'selectedTags' in request.args:
    selectedTags = [int(i) for i in request.args.getlist('selectedTags')]
    tags = selectedTags
    clothGuids = getDB().getClothesByTagIds(tags)
    allClothes = clothes
    filteredClothes = filter(lambda x: x.guid in clothGuids, allClothes)
    tagUsage = getDB().getTagUsage()
    displayTags = filter(lambda x: x[0] in tagUsage and tagUsage[x[0]] > 0, getDB().getTags())
    return render_template('edit_wardrobe.html', clothes=filteredClothes, tags=displayTags, filtered=True, selectedTags=tags)
  tagUsage = getDB().getTagUsage()
  displayTags = filter(lambda x: x[0] in tagUsage and tagUsage[x[0]] > 0, getDB().getTags())
  return render_template('edit_wardrobe.html', clothes=clothes, tags=displayTags, filtered=False)

@app.route('/checkout')
@req_auth
def checkout():
  if 'clothingGUID' in request.args:
    clothingGUID = int(request.args['clothingGUID'])
    getClothing(clothingGUID).checkout()
  return redirect(url_for('use_wardrobe'))

@app.route('/checkin')
@req_auth
def checkin():
  if 'clothingGUID' in request.args:
    clothingGUID = int(request.args['clothingGUID'])
    getClothing(clothingGUID).checkin()
  return redirect(url_for('use_wardrobe'))

@app.route('/use_wardrobe')
@req_auth
def use_wardrobe():
  if 'tag' in request.args: #TODO show "no clothes match search parameters"
    tags = [int(request.args['tag'])]
    if 'selectedTags' in request.args:
      selectedTags = [int(i) for i in request.args.getlist('selectedTags')]
      tags += selectedTags
    return redirect(url_for('use_wardrobe', selectedTags=tags))
  elif 'untag' in request.args:
    selectedTags = [int(i) for i in request.args.getlist('selectedTags')]
    selectedTags.remove(int(request.args['untag']))
    tags = selectedTags
    if len(selectedTags) > 0:
      return redirect(url_for('use_wardrobe', selectedTags=selectedTags))
    else:
      return redirect(url_for('use_wardrobe'))
  elif 'selectedTags' in request.args:
    selectedTags = [int(i) for i in request.args.getlist('selectedTags')]
    tags = selectedTags
    clothGuids = getDB().getClothesByTagIds(tags)
    allClothes = getClothes(True)
    filteredClothes = filter(lambda x: x.guid in clothGuids, allClothes)
    tagUsage = getDB().getTagUsage()
    displayTags = filter(lambda x: x[0] in tagUsage and tagUsage[x[0]] > 0, getDB().getTags())
    return render_template('use_wardrobe.html', clothes=filteredClothes, tags=displayTags, filtered=True, selectedTags=tags)
  tagUsage = getDB().getTagUsage()
  displayTags = filter(lambda x: x[0] in tagUsage and tagUsage[x[0]] > 0, getDB().getTags())
  return render_template('use_wardrobe.html', clothes=getClothes(True), tags=displayTags, filtered=False)

@app.route('/new_clothing', methods=['POST'])
@req_auth
def new_clothing():
  clothing_name = request.form['name']
  clothing_tags = filter(lambda x: len(x) > 0, str(request.form['tags']).split(","))
  newClothGuid = getDB().addCloth(clothing_name)#todo show status if cloth already exists
  for i in clothing_tags:
    getDB().tagCloth(newClothGuid, i)
  return redirect(url_for("edit_wardrobe"))

@app.route('/edit_clothing', methods=['POST'])
@req_auth
def edit_clothing():
  clothing_name = request.form['name'] # TODO: should be alphanumeric and maybe also double quotes + spaces
  clothing_guid = int(request.form['guid']) # TODO: validate

  clothing_tags = filter(lambda x: len(x) > 0, str(request.form['tags']).split(","))
  getDB().updateClothName(clothing_guid, clothing_name)#todo show status if cloth already exists
  getDB().delClothTagAssociations(clothing_guid) #TODO: figure out what's new what's old and only delete the old ones
  for i in clothing_tags:
    getDB().tagCloth(clothing_guid, i)
  return redirect(url_for("edit_wardrobe"))

@app.route('/delete_cloth/<int:id>')
@req_auth
def delete_cloth(id):
  getDB().delCloth(id)
  return redirect(url_for("edit_wardrobe"))

def fbAuth():
  requestURL = "https://www.facebook.com/dialog/oauth?client_id=%s&redirect_uri=%s" % (APP_ID, url_for("fbAuthCallback", _external=True))
  return redirect(requestURL)

def getAppAccessToken():
  return str(json.loads(requests.get('https://graph.facebook.com/v2.3/oauth/access_token?'+
    'client_id=%s&client_secret=%s&grant_type=client_credentials' % (APP_ID, APP_SECRET)
    ).content)["access_token"])

@app.route('/fbAuthCallback')
def fbAuthCallback():
  if "code" in request.args:
    access_token = json.loads(requests.get(
      "https://graph.facebook.com/v2.3/oauth/access_token?" +
      "client_id=%s&" % (APP_ID,) +
      "redirect_uri=%s&" % (url_for("fbAuthCallback", _external=True),) +
      "client_secret=%s&" % (APP_SECRET,) +
      "code=%s" % (request.args["code"],)
      ).content)
    session['token'] = str(access_token["access_token"])
    return redirect(url_for("index"))
  return fbAuth()

def getSessionTokenStatus():
  if 'token' in session:
    token_status = json.loads(requests.get(
      "https://graph.facebook.com/debug_token?" +
      "input_token=%s&" % (session['token'],) +
      "&access_token=%s&" % (getAppAccessToken(),)
      ).content)
    status = {}
    status["user"] = token_status["data"]["user_id"]
    status["valid"] = token_status["data"]["is_valid"]
    return status
  else:
    return {"valid": False}

def getCurrentUserName():
  sessionStatus = getSessionTokenStatus()
  if sessionStatus['valid']:
    return str(json.loads(requests.get("https://graph.facebook.com/v2.7/%s?access_token=%s" % (sessionStatus['user'], getAppAccessToken())).content)["name"])
  return None

def getCurrentUserFirstName():
  return getCurrentUserName().split()[0]

@app.route('/logout')
def logout():
  session.pop('token')
  return redirect(url_for('index'))

@app.route('/add_sample_set')
@req_auth
def add_sample_set():
  colors = ["Coral", "Black", "White", "Pink", "Blue", "Canary"]
  styles = ["Shirt", "Pants", "OCBD", "Jacket", "Tie", "Hat"]
  samples = []
  for i in colors:
    for j in styles:
      samples.append(i + " " + j)

  for i in samples:
    j = i.upper()
    guid = getDB().addCloth(j)
    getDB().tagCloth(guid, j.split()[0])
    getDB().tagCloth(guid, j.split()[1])
  return redirect(url_for("edit_wardrobe"))

if __name__ == '__main__':
  port = int(os.environ.get('PORT', 8080))
  app.config['SERVER_NAME'] = os.environ.get("server_name", "wardrobe-plus-jeffhou.c9users.io")
  app.secret_key = APP_SECRET
  app.run('0.0.0.0', debug=True, port=port)