from flask import Flask, render_template, redirect, url_for, request, g
import sqlite3
import inspect

def connect_db():
  dbConnection = sqlite3.connect("closet.db")
  return dbConnection

def getDB():
  if not hasattr(g, 'sqlite_db'):
    g.sqlite_db = connect_db()
  return g.sqlite_db

def createTable(tableName, tableAttributes, force=True):
  with getDB() as connection:
    cursor = connection.cursor()
    if force:
      cursor.execute("DROP TABLE IF EXISTS %s" % tableName)
    columns = ", ".join([" ".join(attributePair) for attributePair in tableAttributes])
    try:
      cursor.execute("CREATE TABLE %s(Id INTEGER PRIMARY KEY AUTOINCREMENT, %s);" % (tableName, columns))
    except Exception as e:
      print "EXCEPT (%s): " % (inspect.currentframe().f_code.co_name,) + str(e)

def addCloth(clothName):
  connection = getDB()
  with connection:
    cursor = connection.cursor()
    try:
      cursor.execute("INSERT INTO Clothes(Name) VALUES('%s');" % (clothName))
      return getClothGuidByName(clothName)
    except Exception as e:
      print "EXCEPT (%s): " % (inspect.currentframe().f_code.co_name,) + str(e)

def getClothGuidByName(clothName):
    connection = getDB()
    with connection:
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT * FROM Clothes WHERE Name='%s'" % clothName)
            return cursor.fetchone()[0]
        except Exception as e:
            print "EXCEPT (%s): " % (inspect.currentframe().f_code.co_name,) + str(e)

def getCloth(clothId):
  connection = getDB()
  with connection:
    cursor = connection.cursor()
    try:
      cursor.execute("SELECT * FROM Clothes WHERE Id=%s" % (clothId))
      return cursor.fetchall()[0]
    except Exception as e:
      print "EXCEPT (%s): " % (inspect.currentframe().f_code.co_name,) + str(e)

def getClothesDB():
  connection = getDB()
  with connection:
    cursor = connection.cursor()
    try:
      cursor.execute("SELECT * FROM Clothes")
      return cursor.fetchall()
    except Exception as e:
      print "EXCEPT (%s): " % (inspect.currentframe().f_code.co_name,) + str(e)

def delCloth(clothId):
  connection = getDB()
  with connection:
    cursor = connection.cursor()
    try:
      cursor.execute("DELETE FROM Clothes WHERE Id=%s" % (clothId))
      cursor.execute("DELETE FROM ClothesTagsAssociations WHERE ClothId=%s" % (clothId))
    except Exception as e:
      print "EXCEPT (%s): " % (inspect.currentframe().f_code.co_name,) + str(e)

def getTag(tagId):
  connection = getDB()
  with connection:
    cursor = connection.cursor()
    try:
      cursor.execute("SELECT * FROM Tags WHERE Id=%s" % (tagId))
      return cursor.fetchall()[0]
    except Exception as e:
      print "EXCEPT (%s): " % (inspect.currentframe().f_code.co_name,) + str(e)

def getTags():
  connection = getDB()
  with connection:
    cursor = connection.cursor()
    try:
      cursor.execute("SELECT * FROM Tags")
      return [(i[0], str(i[1])) for i in cursor.fetchall()]
    except Exception as e:
      print "EXCEPT (%s): " % (inspect.currentframe().f_code.co_name,) + str(e)

def delTag(tagId):
  connection = getDB()
  with connection:
    cursor = connection.cursor()
    try:
      cursor.execute("DELETE FROM Tags WHERE Id=%s" % (tagId))
    except Exception as e:
      print "EXCEPT (%s): " % (inspect.currentframe().f_code.co_name,) + str(e)

def delClothesTagsAssociations(clothId, tagId):
  connection = getDB()
  with connection:
    cursor = connection.cursor()
    try:
      cursor.execute("DELETE FROM ClothesTagsAssociations WHERE ClothId=%s AND TagId=%s" % (clothId, tagId))
    except Exception as e:
      print "EXCEPT (%s): " % (inspect.currentframe().f_code.co_name,) + str(e)

def tagCloth(clothId, tagString):
  tagString = tagString.lower()
  connection = getDB()
  with connection:
    cursor = connection.cursor()
    # add tag if needed
    try:
      cursor.execute("INSERT INTO Tags(Name) VALUES('%s');" % (tagString))
    except Exception as e:
      print "EXCEPT A(%s): " % (inspect.currentframe().f_code.co_name,) + str(e)
    # TODO: sanitize string inputs
    # get tagId
    tagId = -1
    try:
      cursor.execute("SELECT * FROM Tags WHERE Name=?", (tagString,)) #TODO unique select that excepts if fetchall gets more than one
      tagId = cursor.fetchone()[0]
    except Exception as e:
      print "EXCEPT B(%s): " % (inspect.currentframe().f_code.co_name,) + str(e)
      raise Exception("Could not find tag, should be able to")
    try:
      cursor.execute("INSERT INTO ClothesTagsAssociations(ClothId, TagId) VALUES(%s, %s);" % (clothId, tagId))
    except Exception as e:
      print "EXCEPT C(%s): " % (inspect.currentframe().f_code.co_name,) + str(e)

def getTagIdsForCloth(clothId):
  with getDB() as connection:
    cursor = connection.cursor()
    try:
      cursor.execute("SELECT * FROM ClothesTagsAssociations WHERE ClothId=?", (clothId,))
      return [i[2] for i in cursor.fetchall()]
    except Exception as e:
      print "EXCEPT (%s): " % (inspect.currentframe().f_code.co_name,) + str(e)

def getTagNamesByClothId(clothId):
  tagIds = getTagIdsForCloth(clothId)
  with getDB() as connection:
    cursor = connection.cursor()
    try:
      cursor.execute("SELECT * FROM Tags WHERE Id IN (%s)" % ", ".join([str(i) for i in tagIds]))
      return [str(i[1]) for i in cursor.fetchall()]
    except Exception as e:
      print "EXCEPT (%s): " % (inspect.currentframe().f_code.co_name,) + str(e)

def getTagsByClothId(clothId):
  tagIds = getTagIdsForCloth(clothId)
  with getDB() as connection:
    cursor = connection.cursor()
    try:
      cursor.execute("SELECT * FROM Tags WHERE Id IN (%s)" % ", ".join([str(i) for i in tagIds]))
      return [(i[0], str(i[1])) for i in cursor.fetchall()]
    except Exception as e:
      print "EXCEPT (%s): " % (inspect.currentframe().f_code.co_name,) + str(e)

def getClothesByTagIds(tagIds):
  with getDB() as connection:
    cursor = connection.cursor()
    try:
      unionQueryString = "SELECT DISTINCT ClothId from ClothesTagsAssociations C WHERE (%s)" % " AND ".join([("EXISTS (SELECT 1 FROM ClothesTagsAssociations WHERE TagId=%s AND ClothId=C.ClothId)" % str(i)) for i in tagIds])
      cursor.execute(unionQueryString)
      #cursor.execute("SELECT * FROM ClothesTagsAssociations WHERE TagId IN (%s)" % ", ".join([str(i) for i in tagIds]))
      return [i[0] for i in cursor.fetchall()]
    except Exception as e:
      print "EXCEPT (%s): " % (inspect.currentframe().f_code.co_name,) + str(e)

def updateClothStatus(clothGuid, statusID):
    with getDB() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute("UPDATE Clothes SET InWardrobe=%s WHERE Id=%s" % (str(statusID), clothGuid))
        except Exception as e:
            print "EXCEPT (%s): " % (inspect.currentframe().f_code.co_name,) + str(e)

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
    return render_template('edit_wardrobe.html', clothes=filteredClothes, tags=getTags(), filtered=True, selectedTags=tags)
  return render_template('edit_wardrobe.html', clothes=getClothesListDB(), tags=getTags(), filtered=False)

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