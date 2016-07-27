from flask import Flask, render_template, redirect, url_for, request, g
import sqlite3
import inspect, os

def connect_db(dbName):
  dbConnection = sqlite3.connect(dbName)
  return dbConnection

def getDB():
  if not hasattr(g, 'sqlite_db'):
    g.sqlite_db = connect_db("closet.db")
  return g.sqlite_db

def createTable(tableName, tableAttributes, force=False):
  if force:
    executeDBCode("DROP TABLE IF EXISTS %s" % tableName)
  columns = ", ".join([" ".join(attributePair) for attributePair in tableAttributes])
  executeDBCode("CREATE TABLE %s(Id INTEGER PRIMARY KEY AUTOINCREMENT, %s);" % (tableName, columns))

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

def insert(table, keys, values):
  keysString = ",".join([str(i) for i in keys])
  valuesString = ",".join([str(i) for i in values])
  executeDBCode("INSERT INTO %s(%s) VALUES(%s)" % (table, keysString, valuesString))

def addCloth(clothName):
  insert("Clothes", ["Name"], ["'%s'" % clothName])

def addTag(tagName):
  insert("Tags", ["Name"], ["'%s'" % tagName])

def getClothGuidByName(clothName):
  return executeDBCode("SELECT * FROM Clothes WHERE Name='%s'" % clothName, True)[0][0]

def getCloth(clothId):
  return executeDBCode("SELECT * FROM Clothes WHERE Id=%s" % (clothId), True)[0]

def getClothesDB():
  return executeDBCode("SELECT * FROM Clothes", True)

def getClothsByStatus(status=True):
  if status:
    inWardrobe = 1
  else:
    inWardrobe = 0
  return executeDBCode("SELECT * FROM Clothes WHERE InWardrobe = %s" % (inWardrobe,), True)

def delClothTagAssociations(clothId):
  executeDBCode("DELETE FROM ClothesTagsAssociations WHERE ClothId=%s" % (clothId))

def delCloth(clothId):
  executeDBCode("DELETE FROM Clothes WHERE Id=%s" % (clothId))
  delClothTagAssociations(clothId)

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
  addTag(tagString)
  tagId = executeDBCode("SELECT * FROM Tags WHERE Name='%s'" % (tagString), True)[0][0]
  insert("ClothesTagsAssociations", ["ClothId", "TagId"], [clothId, tagId])

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

def getClothes(sort_=False):
  clothes = getClothesDB()
  clothesList = []
  for i in clothes:
    clothName = str(i[1])
    clothTags = getTagsByClothId(int(i[0])) #TODO need to recast/retype this variable
    clothInWardrobe = bool(i[2])
    clothGuid = int(i[0])
    clothesList.append(Clothing(clothName, clothTags, clothInWardrobe, clothGuid))
  if sort_:
    compatibilityScores = getCompatibilityScores()
    clothesList = sorted(clothesList, key=lambda x: compatibilityScores[x.guid], reverse=True)
  return clothesList

def getClothing(guid):
  for i in getClothes():
    if guid == i.guid:
      return i

class Clothing:
  def __init__(self, name, tags=[], inWardrobe=True, guid=-1):
    self.name = str(name)
    self.guid = guid
    self.tags = tags
    self.inWardrobe = inWardrobe
  def isInWardrobe(self):
    return self.inWardrobe
  def checkin(self):
    self.inWardrobe = True
    updateClothStatus(self.guid, 1)
  def checkout(self):
    self.inWardrobe = False
    updateClothStatus(self.guid, 0)
  def __str__(self):
    return "[Clothing]" + str({"name": self.name, "guid": self.guid,
        "tags": self.tags, "inWardrobe": self.inWardrobe})

def incrementCompatibility(clothId1, clothId2):
  clothId1, clothId2 = sorted((clothId1, clothId2))
  compatibility = executeDBCode("SELECT * FROM ClothCompatibilityUsage WHERE ClothId1 = %s AND ClothId2 = %s LIMIT 1" % (clothId1, clothId2), True)
  if len(compatibility) > 0:
    executeDBCode("UPDATE ClothCompatibilityUsage SET Usage = Usage + 1 WHERE ClothId1 = %s AND ClothId2 = %s" % (clothId1, clothId2))
  else:
    insert("ClothCompatibilityUsage", ("ClothId1", "ClothId2"), (clothId1, clothId2))

def getCompatibilityScores():
  compatibilityScores = {}
  for i in getClothesDB():
    i1 = i[0]
    if i[2] > 0:
      compatibilityScore = 0
      for j in getClothesDB():
        j1 = j[0]
        if not j[2] > 0:
          clothId1, clothId2 = sorted((i1, j1))
          clothingCompatibility = executeDBCode("SELECT * FROM ClothCompatibilityUsage WHERE ClothId1 = %s AND ClothId2 = %s LIMIT 1" % (clothId1, clothId2), True)
          if len(clothingCompatibility) > 0:
            compatibilityScore += clothingCompatibility[0][3]
      compatibilityScores[i1] = compatibilityScore
    else:
      compatibilityScores[i1] = 0
  return compatibilityScores

def incrementAllCompatibility():
  clothesIds = [i[0] for i in getClothsByStatus(False)]
  if len(clothesIds) > 1:
    for i in range(len(clothesIds)):
      for j in range(i + 1, len(clothesIds)):
        incrementCompatibility(clothesIds[i], clothesIds[j])

def createTables(reset=True):
  createTable("Clothes", [["Name", "TEXT UNIQUE"], ["InWardrobe", "SMALLINT DEFAULT 1"], ["Usage", "INTEGER DEFAULT 0"]], reset)
  createTable("ClothCompatibilityUsage", [["ClothId1", "INTEGER"], ["ClothId2", "INTEGER"], ["Usage", "INT DEFAULT 1"], ["UNIQUE(ClothId1, ClothId2)", "ON CONFLICT IGNORE"]], reset)
  createTable("Tags", [["Name", "TEXT UNIQUE"]], reset)
  createTable("ClothesTagsAssociations", [["ClothId", "INTEGER"], ["TagId", "INTEGER"], ["UNIQUE(ClothId, TagId)", "ON CONFLICT IGNORE"]], reset)

@app.route('/')
def index():
  createTables()
  return render_template('landing_menu.html')

@app.route('/save_changes')
def save_changes():
  incrementAllCompatibility()
  return redirect(url_for('edit_wardrobe'))

@app.route('/clear_wardrobe')
def clear_wardrobe():
  createTables(True)
  return redirect(url_for('edit_wardrobe'))

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
    allClothes = getClothes()
    filteredClothes = filter(lambda x: x.guid in clothGuids, allClothes)
    tagUsage = getTagUsage()
    displayTags = filter(lambda x: x[0] in tagUsage and tagUsage[x[0]] > 0, getTags())
    return render_template('edit_wardrobe.html', clothes=filteredClothes, tags=displayTags, filtered=True, selectedTags=tags)
  tagUsage = getTagUsage()
  displayTags = filter(lambda x: x[0] in tagUsage and tagUsage[x[0]] > 0, getTags())
  return render_template('edit_wardrobe.html', clothes=getClothes(), tags=displayTags, filtered=False)

@app.route('/checkout')
def checkout():
  if 'clothingGUID' in request.args:
    clothingGUID = int(request.args['clothingGUID'])
    getClothing(clothingGUID).checkout()
  return redirect(url_for('use_wardrobe'))

@app.route('/checkin')
def checkin():
  if 'clothingGUID' in request.args:
    clothingGUID = int(request.args['clothingGUID'])
    getClothing(clothingGUID).checkin()
  return redirect(url_for('use_wardrobe'))

@app.route('/use_wardrobe')
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
    clothGuids = getClothesByTagIds(tags)
    allClothes = getClothes(True)
    filteredClothes = filter(lambda x: x.guid in clothGuids, allClothes)
    tagUsage = getTagUsage()
    displayTags = filter(lambda x: x[0] in tagUsage and tagUsage[x[0]] > 0, getTags())
    return render_template('use_wardrobe.html', clothes=filteredClothes, tags=displayTags, filtered=True, selectedTags=tags)
  tagUsage = getTagUsage()
  displayTags = filter(lambda x: x[0] in tagUsage and tagUsage[x[0]] > 0, getTags())
  return render_template('use_wardrobe.html', clothes=getClothes(True), tags=displayTags, filtered=False)

@app.route('/new_clothing', methods=['POST'])
def new_clothing():
  clothing_name = request.form['name']
  clothing_tags = filter(lambda x: len(x) > 0, str(request.form['tags']).split(","))
  addCloth(clothing_name)#todo show status if cloth already exists
  newClothGuid = getClothGuidByName(clothing_name)
  for i in clothing_tags:
    tagCloth(newClothGuid, i)
  return redirect(url_for("edit_wardrobe"))

@app.route('/delete_cloth/<int:id>')
def delete_cloth(id):
  delCloth(id)
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
    addCloth(i)
    guid = getClothGuidByName(i)
    tagCloth(guid, i.split()[0])
    tagCloth(guid, i.split()[1])
  return redirect(url_for("edit_wardrobe"))

if __name__ == '__main__':
  port = int(os.environ.get('PORT', 8080))
  app.run('0.0.0.0', debug=True, port=port)