from uuid import UUID, uuid4
from starlette.testclient import TestClient
from fasthtml import FastHTML
from session_normalizer_middleware.middleware import (
    SessionNormalizerMiddleware,
)
import unittest


def get_cli(app):
    return app, TestClient(app), app.route


class SessionNormalizerTests(unittest.TestCase):

    def test_custom_str_serialization_success(self):
        """
        Utilizing UUID as a real-world example because it implements
        a custom __str__ method and is a likely candidate for something
        that would actually need to be saved in a session cookie.
        """
        app, cli, route = get_cli(
            FastHTML(sess_cls=SessionNormalizerMiddleware)
        )

        @app.get("/")
        def _(session, item_id: UUID):
            session["item_id"] = item_id
            return "OK"

        response = cli.get(
            "/?item_id=36621c53-55c3-11ef-b14b-c45ab1ddc9ad"
        ).text
        self.assertEqual(response, "OK")

    def test_list_normalize_success(self):
        app, cli, route = get_cli(
            FastHTML(sess_cls=SessionNormalizerMiddleware)
        )

        @app.get("/")
        def _(session):
            session["uuid_list"] = [uuid4() for _ in range(4)]
            return "OK"

        response = cli.get("/").text
        self.assertEqual(response, "OK")

    def test_dict_normalize_success(self):
        app, cli, route = get_cli(
            FastHTML(sess_cls=SessionNormalizerMiddleware)
        )

        @app.get("/")
        def _(session):
            session["uuid_dict_list"] = [{uuid4(): uuid4()} for _ in range(4)]
            return "OK"

        response = cli.get("/").text
        self.assertEqual(response, "OK")

    def test_dunder_json_normalize_success(self):
        app, cli, route = get_cli(
            FastHTML(sess_cls=SessionNormalizerMiddleware)
        )

        class HasDunderJSONMethod:
            def __json__(self):
                return {"hello": "world"}

        class HasDunderJSONAttr:
            __json__ = {"hello": "world"}

        @app.get("/")
        def _(session):
            session["dunder_json_method"] = HasDunderJSONMethod()
            session["dunder_json_attr"] = HasDunderJSONAttr()
            return "OK"

        response = cli.get("/").text
        self.assertEqual(response, "OK")

    def test_dunder_dict_normalize_success(self):
        app, cli, route = get_cli(
            FastHTML(sess_cls=SessionNormalizerMiddleware)
        )

        class HasDunderDict:
            pass

        @app.get("/")
        def _(session):
            session["uuid_dict_list"] = HasDunderDict()
            return "OK"

        response = cli.get("/").text
        self.assertEqual(response, "OK")

    def test_raises_type_error(self):
        """
        Key to this test is the fact that the test class implements
        __slots__, which means it has no __dict__ attribute, and it
        also implements no custom __str__ method.
        """
        app, cli, route = get_cli(
            FastHTML(sess_cls=SessionNormalizerMiddleware)
        )

        class HasNoSterializationLogic:
            __slots__ = ["hello", "world"]

        @app.get("/")
        def _(session):
            session["uuid_dict_list"] = HasNoSterializationLogic()
            return "OK"

        with self.assertRaises(TypeError):
            cli.get("/").text

    def test_uuid_serialization_failure(self):
        app, cli, route = get_cli(FastHTML())

        @app.get("/")
        def _(session, item_id: UUID):
            session["item_id"] = item_id
            return "OK"

        with self.assertRaises(TypeError):
            cli.get("/?item_id=36621c53-55c3-11ef-b14b-c45ab1ddc9ad").text
