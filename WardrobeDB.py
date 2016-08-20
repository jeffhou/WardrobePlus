import sqlite3

class WardrobeDB:
  def __init__(self):
    pass

  # Import reqs: sqlite3
  # Usage: getDB()
  def connect_db(self, dbName):
    """Establishes SQLite connection.

    Args:
      dbName (str): The name/path of the SQLite database.

    Returns:
      sqlite3.connection

    """
    dbConnection = sqlite3.connect(dbName)
    return dbConnection

  # Import reqs: from flask import g
  # Dependencies: connect_db()
  # Usage: executeDBCode()
  def getDB(self):
    """Emulates a global singleton pattern for the connection to the SQLite DB

    TODO: Extract magic string "closet.db" into global constant.
    TODO: Extract dependency on flask.g so that this function and other SQLite
          functions can be encapsulated into a separate module and/or class.

    Returns:
      sqlite3.connection: Connection to the main DB.

    """
    if not hasattr(self, 'sqlite_db'):
      self.sqlite_db = self.connect_db("closet.db")
    return self.sqlite_db

  def closeDB(self):
    if hasattr(self, 'sqlite_db'):
      self.sqlite_db.close()

  # Dependencies: executeDBCode()
  # Usage: createTables()
  def createTable(self, tableName, tableAttributes, force=False):
    """ Wrapper for SQLite code to create table

    TODO: refactor the format string usage into built-in SQL strings

    Args:
      tableName (str): name of table
      tableAttributes ([(str, str), ..]): attributes of the table, mostly columns
      force (bool): Drops the table if True, essentially clearing the table

    """
    if force:
      self.executeDBCode("DROP TABLE IF EXISTS %s" % tableName)
    columns = ", ".join([" ".join(attributePair) for attributePair in tableAttributes])
    self.executeDBCode("CREATE TABLE %s(Id INTEGER PRIMARY KEY AUTOINCREMENT, %s);" % (tableName, columns))

  # Dependencies: getDB()
  # Usage: TOO MANY
  def executeDBCode(self, dbCode, returnsValues=False, vars=None):
    """ Wrapper for Generic SQLite code

    TODO: outline the actual usage of this function.

    Args:
      tableName (str): name of table
      tableAttributes ([(str, str), ..]): attributes of the table, mostly columns
      force (bool): Drops the table if True, essentially clearing the table

    """
    connection = self.getDB()
    with connection:
      cursor = connection.cursor()
      try:
        if vars == None:
          cursor.execute(dbCode)
        else:
          cursor.execute(dbCode, vars)
        if returnsValues:
          return cursor.fetchall()
      except Exception as e:
        print "EXCEPT (%s): " % (dbCode,) + str(e)

  # Dependencies: executeDBCode()
  # Usage: addCloth(), addTag(), tagCloth(), incrementCompatibility()
  def insert(self, table, keys, values):
    """ Wrapper for SQLite INSERT

    TODO: standardize name of parameters across functions

    Args:
      table (str): name of table
      keys ([str]): names of columns
      values ([str]): names of values, ordered the same as keys

    """
    keysString = ",".join([str(i) for i in keys])
    valuesString = ",".join([str(i) for i in values])
    self.executeDBCode("INSERT INTO %s(%s) VALUES(%s)" % (table, keysString, valuesString))

  # Dependencies: insert()
  # Usage: new_clothing(), add_sample_set()
  def addCloth(self, clothName):
    """ Inserts new cloth into DB

    Args:
      clothName (str): name of cloth

    """
    self.insert("Clothes", ["Name"], ["'%s'" % clothName])

  # Dependencies: tagExists()
  # Usage: tagCloth()
  def addTag(self, name):
    if not self.tagExists(name):
      self.insert("Tags", ["Name"], ["'%s'" % name])

  # Dependencies: executeDBCode()
  # Usage: addTag()
  def tagExists(self, name):
    return self.executeDBCode("select exists(select 1 from Tags where Name=?)", True, vars=(name,))[0][0] == 1

  def getClothGuidByName(self, clothName):
    return self.executeDBCode("SELECT * FROM Clothes WHERE Name='%s'" % clothName, True)[0][0]

  def getCloth(self, clothId):
    return self.executeDBCode("SELECT * FROM Clothes WHERE Id=%s" % (clothId), True)[0]

  def getClothesDB(self, ):
    return self.executeDBCode("SELECT * FROM Clothes", True)

  def getClothsByStatus(self, status=True):
    if status:
      inWardrobe = 1
    else:
      inWardrobe = 0
    return self.executeDBCode("SELECT * FROM Clothes WHERE InWardrobe = %s" % (inWardrobe,), True)

  def delClothTagAssociations(self, clothId):
    self.executeDBCode("DELETE FROM ClothesTagsAssociations WHERE ClothId=%s" % (clothId))

  def delCloth(self, clothId):
    self.executeDBCode("DELETE FROM Clothes WHERE Id=%s" % (clothId))
    self.delClothTagAssociations(clothId)

  def getTag(self, tagId):
    return self.executeDBCode("SELECT * FROM Tags WHERE Id=%s" % (tagId), True)[0]

  def getTagUsage(self):
    usageDict = {}
    for i in self.executeDBCode("SELECT t.id, c.cnt FROM Tags t INNER JOIN (SELECT TagId, count(TagId) as cnt FROM ClothesTagsAssociations GROUP BY TagId) c ON t.id = c.TagId", True):
      usageDict[i[0]] = i[1]
    return usageDict

  def getTags(self):
    return [(i[0], str(i[1])) for i in self.executeDBCode("SELECT * FROM Tags", True)]

  def delTag(self, tagId):
    self.executeDBCode("DELETE FROM Tags WHERE Id=%s" % (tagId))

  def delClothesTagsAssociations(self, clothId, tagId):
    self.executeDBCode("DELETE FROM ClothesTagsAssociations WHERE ClothId=%s AND TagId=%s" % (clothId, tagId))

  def tagCloth(self, clothId, tagString):
    tagString = tagString.lower()
    self.addTag(tagString)
    tagId = self.executeDBCode("SELECT * FROM Tags WHERE Name='%s'" % (tagString), True)[0][0]
    self.insert("ClothesTagsAssociations", ["ClothId", "TagId"], [clothId, tagId])

  def getTagIdsForCloth(self, clothId):
    return [i[2] for i in self.executeDBCode("SELECT * FROM ClothesTagsAssociations WHERE ClothId=%s" % (clothId), True)]

  def getTagNamesByClothId(self, clothId):
    tagIds = self.getTagIdsForCloth(clothId)
    return [str(i[1]) for i in self.executeDBCode("SELECT * FROM Tags WHERE Id IN (%s)" % ", ".join([str(i) for i in tagIds]), True)]

  def getTagsByClothId(self, clothId):
    tagIds = self.getTagIdsForCloth(clothId)
    return [(i[0], str(i[1])) for i in self.executeDBCode("SELECT * FROM Tags WHERE Id IN (%s)" % ", ".join([str(i) for i in tagIds]), True)]

  def getClothesByTagIds(self, tagIds):
    unionQueryString = "SELECT DISTINCT ClothId from ClothesTagsAssociations C WHERE (%s)" % " AND ".join([("EXISTS (SELECT 1 FROM ClothesTagsAssociations WHERE TagId=%s AND ClothId=C.ClothId)" % str(i)) for i in tagIds])
    return [i[0] for i in self.executeDBCode(unionQueryString, True)]

  def updateClothStatus(self, clothGuid, statusID):
    self.executeDBCode("UPDATE Clothes SET InWardrobe=%s WHERE Id=%s" % (str(statusID), clothGuid))

  def updateAllClothesStatus(self, statusID):
    self.executeDBCode("UPDATE Clothes SET InWardrobe=?", vars=(statusID,))

  def updateClothName(self, clothGuid, clothName):
    self.executeDBCode("UPDATE Clothes SET Name=? WHERE Id=?", vars=(str(clothName), clothGuid))

  def incrementUsage(self, clothGuid):
    self.insert("ClothesUsage", ["ClothId"], [clothGuid])

  def getUsage(self, clothGuid):
    return self.executeDBCode("SELECT Count(1) FROM ClothesUsage WHERE ClothId=?;", True, vars=(clothGuid,))[0][0]

  def createTables(self, reset=False):
    self.createTable("Clothes", [["Name", "TEXT UNIQUE"], ["InWardrobe", "SMALLINT DEFAULT 1"], ["Usage", "INTEGER DEFAULT 0"]], reset)
    self.createTable("ClothCompatibilityUsage", [["ClothId1", "INTEGER"], ["ClothId2", "INTEGER"], ["Usage", "INT DEFAULT 1"], ["UNIQUE(ClothId1, ClothId2)", "ON CONFLICT IGNORE"]], reset)
    self.createTable("Tags", [["Name", "TEXT UNIQUE"]], reset)
    self.createTable("ClothesTagsAssociations", [["ClothId", "INTEGER"], ["TagId", "INTEGER"], ["UNIQUE(ClothId, TagId)", "ON CONFLICT IGNORE"]], reset)
    self.createTable("ClothesUsage", [["ClothId", "INTEGER"], ["Timestamp", "DATETIME DEFAULT CURRENT_TIMESTAMP"]], reset)
