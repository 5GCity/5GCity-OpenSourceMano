#import pymongo
from pymongo import MongoClient
from dbbase import DbException, dbbase
from http import HTTPStatus

class dbmongo(dbbase):

    def __init__(self):
        pass

    def db_connect(self, config):
        try:
            self.client = MongoClient(config["host"], config["port"])
            self.db = self.client[config["name"]]
            # get data to try a connection
            self.db.users.find_one({"username": "admin"})
        except Exception as e:  # TODO refine
            raise DbException(str(e))

    def db_disconnect(self):
        pass  # TODO

    @staticmethod
    def _format_filter(filter):
        try:
            db_filter = {}
            for query_k, query_v in filter.items():
                dot_index = query_k.rfind(".")
                if dot_index > 1 and query_k[dot_index+1:] in ("eq", "ne", "gt", "gte", "lt", "lte", "cont",
                                                               "ncont", "neq"):
                    operator = "$" + query_k[dot_index+1:]
                    if operator == "$neq":
                        operator = "$nq"
                    k = query_k[:dot_index]
                else:
                    operator = "$eq"
                    k = query_k

                v = query_v
                if isinstance(v, list):
                    if operator in ("$eq", "$cont"):
                        operator = "$in"
                        v = query_v
                    elif operator in ("$ne", "$ncont"):
                        operator = "$nin"
                        v = query_v
                    else:
                        v = query_v.join(",")

                if operator in ("$eq", "$cont"):
                    # v cannot be a comma separated list, because operator would have been changed to $in
                    db_filter[k] = v
                elif operator == "$ncount":
                    # v cannot be a comma separated list, because operator would have been changed to $nin
                    db_filter[k] = {"$ne": v}
                else:
                    # maybe db_filter[k] exist. e.g. in the query string for values between 5 and 8: "a.gt=5&a.lt=8"
                    if k not in db_filter:
                        db_filter[k] = {}
                    db_filter[k][operator] = v

            return db_filter
        except Exception as e:
            raise DbException("Invalid query string filter at {}:{}. Error: {}".format(query_k, v, e),
                              http_code=HTTPStatus.BAD_REQUEST.value)


    def get_list(self, table, filter={}):
        try:
            l = []
            collection = self.db[table]
            rows = collection.find(self._format_filter(filter))
            for row in rows:
                l.append(row)
            return l
        except DbException:
            raise
        except Exception as e:  # TODO refine
            raise DbException(str(e))

    def get_one(self, table, filter={}, fail_on_empty=True, fail_on_more=True):
        try:
            if filter:
                filter = self._format_filter(filter)
            collection = self.db[table]
            if not (fail_on_empty and fail_on_more):
                return collection.find_one(filter)
            rows = collection.find(filter)
            if rows.count() == 0:
                if fail_on_empty:
                    raise DbException("Not found entry with filter='{}'".format(filter), HTTPStatus.NOT_FOUND.value)
                return None
            elif rows.count() > 1:
                if fail_on_more:
                    raise DbException("Found more than one entry with filter='{}'".format(filter),
                                      HTTPStatus.CONFLICT.value)
            return rows[0]
        except Exception as e:  # TODO refine
            raise DbException(str(e))

    def del_list(self, table, filter={}):
        try:
            collection = self.db[table]
            rows = collection.delete_many(self._format_filter(filter))
            return {"deleted": rows.deleted_count}
        except DbException:
            raise
        except Exception as e:  # TODO refine
            raise DbException(str(e))

    def del_one(self, table, filter={}, fail_on_empty=True):
        try:
            collection = self.db[table]
            rows = collection.delete_one(self._format_filter(filter))
            if rows.deleted_count == 0:
                if fail_on_empty:
                    raise DbException("Not found entry with filter='{}'".format(filter), HTTPStatus.NOT_FOUND.value)
                return None
            return {"deleted": rows.deleted_count}
        except Exception as e:  # TODO refine
            raise DbException(str(e))

    def create(self, table, indata):
        try:
            collection = self.db[table]
            data = collection.insert_one(indata)
            return data.inserted_id
        except Exception as e:  # TODO refine
            raise DbException(str(e))

    def set_one(self, table, filter, update_dict, fail_on_empty=True):
        try:
            collection = self.db[table]
            rows = collection.update_one(self._format_filter(filter), {"$set": update_dict})
            if rows.updated_count == 0:
                if fail_on_empty:
                    raise DbException("Not found entry with filter='{}'".format(filter), HTTPStatus.NOT_FOUND.value)
                return None
            return {"deleted": rows.deleted_count}
        except Exception as e:  # TODO refine
            raise DbException(str(e))

    def replace(self, table, id, indata, fail_on_empty=True):
        try:
            collection = self.db[table]
            rows = collection.replace_one({"_id": id}, indata)
            if rows.modified_count == 0:
                if fail_on_empty:
                    raise DbException("Not found entry with filter='{}'".format(filter), HTTPStatus.NOT_FOUND.value)
                return None
            return {"replace": rows.modified_count}
        except Exception as e:  # TODO refine
            raise DbException(str(e))
