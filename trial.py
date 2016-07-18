import sqlite3

dbConnection = None

def connectDB():
  dbConnection = sqlite3.connect("closet.db")
  return dbConnection

def getDB():
  global dbConnection
  if dbConnection == None:
    dbConnection = connectDB()
  return dbConnection

def closeDB():
  global dbConnection
  if dbConnection != None:
    dbConnection.close()

def createTable(tableName, tableAttributes, force=True):
  with getDB() as connection:
    cursor = connection.cursor()
    if force:
      cursor.execute("DROP TABLE IF EXISTS %s" % tableName)
    columns = ", ".join([" ".join(attributePair) for attributePair in tableAttributes])
    try:
      cursor.execute("CREATE TABLE %s(Id INTEGER PRIMARY KEY AUTOINCREMENT, %s);" % (tableName, columns))
    except Exception as e:
      print "EXCEPT: " + str(e)

def addCloth(clothName):
  connection = getDB()
  with connection:
    cursor = connection.cursor()
    try:
      cursor.execute("INSERT INTO Clothes(Name) VALUES('%s');" % (clothName))
    except Exception as e:
      print "EXCEPT: " + str(e)

def getCloth(clothId):
  connection = getDB()
  with connection:
    cursor = connection.cursor()
    try:
      cursor.execute("SELECT * FROM Clothes WHERE Id=%s" % (clothId))
      return cursor.fetchall()[0]
    except Exception as e:
      print "EXCEPT: " + str(e)

def delCloth(clothId):
  connection = getDB()
  with connection:
    cursor = connection.cursor()
    try:
      cursor.execute("DELETE FROM Clothes WHERE Id=%s" % (clothId))
    except Exception as e:
      print "EXCEPT: " + str(e)

def getTag(tagId):
  connection = getDB()
  with connection:
    cursor = connection.cursor()
    try:
      cursor.execute("SELECT * FROM Tags WHERE Id=%s" % (tagId))
      return cursor.fetchall()[0]
    except Exception as e:
      print "EXCEPT: " + str(e)

def getTags(tagId):
  connection = getDB()
  with connection:
    cursor = connection.cursor()
    try:
      cursor.execute("SELECT * FROM Tags")
      return cursor.fetchall()
    except Exception as e:
      print "EXCEPT: " + str(e)

def delTag(tagId):
  connection = getDB()
  with connection:
    cursor = connection.cursor()
    try:
      cursor.execute("DELETE FROM Tags WHERE Id=%s" % (tagId))
    except Exception as e:
      print "EXCEPT: " + str(e)

def delClothesTagsAssociations(clothId, tagId):
  connection = getDB()
  with connection:
    cursor = connection.cursor()
    try:
      cursor.execute("DELETE FROM ClothesTagsAssociations WHERE ClothId=%s AND TagId=%s" % (clothId, tagId))
    except Exception as e:
      print "EXCEPT: " + str(e)

def tagCloth(clothId, tagString):
  connection = getDB()
  with connection:
    cursor = connection.cursor()
    # add tag if needed
    try:
      cursor.execute("INSERT INTO Tags(Name) VALUES('%s');" % (tagString))
    except Exception as e:
      print "Except: " + str(e)
    # TODO: sanitize string inputs
    # get tagId
    tagId = -1
    try:
      cursor.execute("SELECT * FROM Tags WHERE Name=?", (tagString,)) #TODO unique select that excepts if fetchall gets more than one
      tagId = cursor.fetchone()[0]
    except Exception as e:
      print "Except: " + str(e)
      raise Exception("Could not find tag, should be able to")
    try:
      cursor.execute("INSERT INTO ClothesTagsAssociations(ClothId, TagId) VALUES(%s, %s);" % (clothId, tagId))
    except Exception as e:
      print "Except: " + str(e)

def getTagIdsForCloth(clothId):
  with getDB() as connection:
    cursor = connection.cursor()
    try:
      cursor.execute("SELECT * FROM ClothesTagsAssociations WHERE ClothId=?", (clothId,))
      return [i[2] for i in cursor.fetchall()]
    except Exception as e:
      print "Except: " + str(e)

def getTagNamesByClothId(clothId):
  tagIds = getTagIdsForCloth(clothId)
  with getDB() as connection:
    cursor = connection.cursor()
    try:
      cursor.execute("SELECT * FROM Tags WHERE Id IN (%s)" % ", ".join([str(i) for i in tagIds]))
      return [str(i[1]) for i in cursor.fetchall()]
    except Exception as e:
      print "Except: " + str(e)

def getClothesByTagIds(tagIds):
  with getDB() as connection:
    cursor = connection.cursor()
    try:
      unionQueryString = "SELECT DISTINCT ClothId from ClothesTagsAssociations C WHERE (%s)" % " AND ".join([("EXISTS (SELECT 1 FROM ClothesTagsAssociations WHERE TagId=%s AND ClothId=C.ClothId)" % str(i)) for i in tagIds])
      cursor.execute(unionQueryString)
      #cursor.execute("SELECT * FROM ClothesTagsAssociations WHERE TagId IN (%s)" % ", ".join([str(i) for i in tagIds]))
      return [i[0] for i in cursor.fetchall()]
    except Exception as e:
      print "Except: " + str(e)

createTable("Clothes", [["Name", "TEXT"]])
createTable("Tags", [["Name", "TEXT UNIQUE"]])
createTable("ClothesTagsAssociations", [["ClothId", "INTEGER"], ["TagId", "INTEGER"], ["UNIQUE(ClothId, TagId)", "ON CONFLICT IGNORE"]])
tagCloth(1, "Korean")
tagCloth(1, "Chinese")
tagCloth(2, "Pants")
tagCloth(2, "Chinese")
tagCloth(1, "blah")
getClothesByTagIds([2])