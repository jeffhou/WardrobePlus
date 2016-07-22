from flask import Flask, render_template, redirect, url_for, request, g
import sqlite3
import inspect

def connect_db(dbName):
  dbConnection = sqlite3.connect(dbName)
  return dbConnection

def getDB():
  if not hasattr(g, 'sqlite_db'):
    g.sqlite_db = connect_db("closet.db")
  return g.sqlite_db

def createTable(tableName, tableAttributes, force=True):
  if force:
    executeDBCode("DROP TABLE IF EXISTS %s" % tableName)
  columns = ", ".join([" ".join(attributePair) for attributePair in tableAttributes])
  executeDBCode("CREATE TABLE %s(Id INTEGER PRIMARY KEY AUTOINCREMENT, %s);" % (tableName, columns), False)

def executeDBCode(dbCode, returnsValues=False):
  connection = getDB()
  with connection:
    cursor = connection.cursor()
    try:
      cursor.execute(dbCode)
      if returnsValues:
        return cursor.fetchall()
    except Exception as e:
      print "EXCEPT (%s): " % (dbCode,) + str(e)

def addCloth(clothName):
  executeDBCode("INSERT INTO Clothes(Name) VALUES('%s');" % (clothName), False)
  return getClothGuidByName(clothName)

def getClothGuidByName(clothName):
  return executeDBCode("SELECT * FROM Clothes WHERE Name='%s'" % clothName, True)[0][0]

def getCloth(clothId):
  return executeDBCode("SELECT * FROM Clothes WHERE Id=%s" % (clothId), True)[0]

def getClothesDB():
  return executeDBCode("SELECT * FROM Clothes", True)

def delCloth(clothId):
  executeDBCode("DELETE FROM Clothes WHERE Id=%s" % (clothId))
  executeDBCode("DELETE FROM ClothesTagsAssociations WHERE ClothId=%s" % (clothId))

def getTag(tagId):
  return executeDBCode("SELECT * FROM Tags WHERE Id=%s" % (tagId), True)[0]

def getTagUsage():
  usageDict = {}
  for i in executeDBCode("SELECT t.id, c.cnt FROM Tags t INNER JOIN (SELECT TagId, count(TagId) as cnt FROM ClothesTagsAssociations GROUP BY TagId) c ON t.id = c.TagId", True):
    usageDict[i[0]] = i[1]
  return usageDict

def getTags():
  return [(i[0], str(i[1])) for i in executeDBCode("SELECT * FROM Tags", True)]

def delTag(tagId):
  executeDBCode("DELETE FROM Tags WHERE Id=%s" % (tagId))

def delClothesTagsAssociations(clothId, tagId):
  executeDBCode("DELETE FROM ClothesTagsAssociations WHERE ClothId=%s AND TagId=%s" % (clothId, tagId))

def tagCloth(clothId, tagString):
  tagString = tagString.lower()
  executeDBCode("INSERT INTO Tags(Name) VALUES('%s');" % (tagString)) #add tag, # TODO: sanitize string inputs
  tagId = executeDBCode("SELECT * FROM Tags WHERE Name='%s'" % (tagString), True)[0][0]
  executeDBCode("INSERT INTO ClothesTagsAssociations(ClothId, TagId) VALUES(%s, %s);" % (clothId, tagId))

def getTagIdsForCloth(clothId):
  return [i[2] for i in executeDBCode("SELECT * FROM ClothesTagsAssociations WHERE ClothId=%s" % (clothId), True)]

def getTagNamesByClothId(clothId):
  tagIds = getTagIdsForCloth(clothId)
  return [str(i[1]) for i in executeDBCode("SELECT * FROM Tags WHERE Id IN (%s)" % ", ".join([str(i) for i in tagIds]), True)]

def getTagsByClothId(clothId):
  tagIds = getTagIdsForCloth(clothId)
  return [(i[0], str(i[1])) for i in executeDBCode("SELECT * FROM Tags WHERE Id IN (%s)" % ", ".join([str(i) for i in tagIds]), True)]

def getClothesByTagIds(tagIds):
  unionQueryString = "SELECT DISTINCT ClothId from ClothesTagsAssociations C WHERE (%s)" % " AND ".join([("EXISTS (SELECT 1 FROM ClothesTagsAssociations WHERE TagId=%s AND ClothId=C.ClothId)" % str(i)) for i in tagIds])
  return [i[0] for i in executeDBCode(unionQueryString, True)]

def updateClothStatus(clothGuid, statusID):
  executeDBCode("UPDATE Clothes SET InWardrobe=%s WHERE Id=%s" % (str(statusID), clothGuid))

app = Flask(__name__)

@app.teardown_appcontext
def closeDB(error):
  if hasattr(g, 'sqlite_db'):
    g.sqlite_db.close()

def getClothesListDB():
    clothes = getClothesDB()
    clothesList = []
    for i in clothes:
        clothName = str(i[1])
        clothTags = getTagsByClothId(int(i[0])) #TODO need to recast/retype this variable
        clothInWardrobe = bool(i[2])
        clothGuid = int(i[0])
        clothesList.append(ClothingDB(clothName, clothTags, clothInWardrobe, clothGuid))
    return clothesList

def getClothing(guid):
    for i in getClothesListDB():
        if guid == i.guid:
            return i

class ClothingDB:
    def __init__(self, name, tags=[], inWardrobe=True, guid=-1):
        self.name = str(name)
        self.guid = guid
        self.tags = tags
        self.inWardrobe = inWardrobe #TODO: update
    def isInWardrobe(self):
        return self.inWardrobe
    def checkin(self):
        self.inWardrobe = True
        updateClothStatus(self.guid, 1) #should update after any change
    def checkout(self):
        self.inWardrobe = False
        updateClothStatus(self.guid, 0) #should update after any change
    def __str__(self):
        return "[ClothingDB]" + str({"name": self.name, "guid": self.guid,
            "tags": self.tags, "inWardrobe": self.inWardrobe})

@app.route('/')
def index():
    createTable("Clothes", [["Name", "TEXT UNIQUE"], ["InWardrobe", "SMALLINT DEFAULT 1"]])
    createTable("Tags", [["Name", "TEXT UNIQUE"]])
    createTable("ClothesTagsAssociations", [["ClothId", "INTEGER"], ["TagId", "INTEGER"], ["UNIQUE(ClothId, TagId)", "ON CONFLICT IGNORE"]])
    return render_template('landing_menu.html')

@app.route('/edit_wardrobe', methods=['GET'])
def edit_wardrobe():
  if 'tag' in request.args: #TODO show "no clothes match search parameters"
    tags = [int(request.args['tag'])]
    if 'selectedTags' in request.args:
      selectedTags = [int(i) for i in request.args.getlist('selectedTags')]
      tags += selectedTags
    return redirect(url_for('edit_wardrobe', selectedTags=tags))
  elif 'untag' in request.args:
    selectedTags = [int(i) for i in request.args.getlist('selectedTags')]
    #print selectedTags
    selectedTags.remove(int(request.args['untag']))
    tags = selectedTags
    if len(selectedTags) > 0:
      return redirect(url_for('edit_wardrobe', selectedTags=selectedTags))
    else:
      return redirect(url_for('edit_wardrobe'))
  elif 'selectedTags' in request.args:
    selectedTags = [int(i) for i in request.args.getlist('selectedTags')]
    tags = selectedTags
    clothGuids = getClothesByTagIds(tags)
    allClothes = getClothesListDB()
    filteredClothes = filter(lambda x: x.guid in clothGuids, allClothes)
    tagUsage = getTagUsage()
    displayTags = filter(lambda x: x[0] in tagUsage and tagUsage[x[0]] > 0, getTags())
    return render_template('edit_wardrobe.html', clothes=filteredClothes, tags=displayTags, filtered=True, selectedTags=tags)
  tagUsage = getTagUsage()
  displayTags = filter(lambda x: x[0] in tagUsage and tagUsage[x[0]] > 0, getTags())
  return render_template('edit_wardrobe.html', clothes=getClothesListDB(), tags=displayTags, filtered=False)

@app.route('/begin_session')
def begin_session():
    return redirect(url_for("sessionCheckout"))

@app.route('/new_clothing', methods=['POST'])
def new_clothing():
    clothing_name = request.form['name']
    clothing_tags = filter(
            lambda x: len(x) > 0, str(request.form['tags']).split(","))
    newClothGuid = addCloth(clothing_name)#todo show status if cloth already exists
    for i in clothing_tags:
        tagCloth(newClothGuid, i)
    return redirect(url_for("edit_wardrobe"))

@app.route('/remove_clothing', methods=['GET', 'POST'])
def remove_clothing():
    return render_template('delete_clothing.html', clothes=getClothesListDB())

@app.route('/delete_cloth/<int:id>')
def delete_cloth(id):
    delCloth(id)
    return redirect(url_for("edit_wardrobe"))

def delete_clothing():
    clothGuid = int(request.form.get('comp_select'))
    delCloth(clothGuid)
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
      guid = addCloth(i)
      tagCloth(guid, i.split()[0])
      tagCloth(guid, i.split()[1])
    return redirect(url_for("edit_wardrobe"))

@app.route('/session#checkout')
def sessionCheckout():
    if 'clothingGUID' in request.args:
        clothingGUID = int(request.args['clothingGUID'])
        getClothing(clothingGUID).checkout()
    return render_template('session.html', clothes=getClothesListDB())

@app.route('/session#return')
def sessionReturn():
    if 'clothingGUID' in request.args:
        clothingGUID = int(request.args['clothingGUID'])
        getClothing(clothingGUID).checkin()
    return render_template('session.html', clothes=getClothesListDB())

if __name__ == '__main__':
    app.run('0.0.0.0', debug=True, port=8080)