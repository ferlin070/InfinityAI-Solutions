from postgrest.exceptions import APIError


class BaseRepo:
    def _exec(self, query):
        try:
            return query.execute()
        except APIError as e:
            if e.code == "204":
                return None
            raise
