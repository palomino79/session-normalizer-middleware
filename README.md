## Requirements

- Python 3.6+
- FastHTML 0.4.0+

## Issues and Contributions

If you encounter any issues or have suggestions for improvements, please use the [GitHub Issues](https://github.com/palomino79/session_normalizer_middleware/issues) page to report them.

## Usage

SessionNormalizerMiddleware provides a drop-in replacement for the standard fasthtml session middleware class. This session middleware class aggressively converts session stored data to a format that can be serialized.

Simple example:

```
from fasthtml_sessionnormalizer.middleware import SessionNormalizerMiddleware
from fasthtml import FastHTML


app = FastHTML(sess_cls=SessionNormalizerMiddleware)

@app.get("/")
def default(session, item_id: UUID):
    session["item_id"] = item_id
```

The above endpoint will successfully store a `UUID` object in the session, converting it to a string before returning it to the user. Note: objects that only provide a `__str__` method that matches that of the default `object` class as the sole mechanism of conversion will not be serialized, as the assumption is that the default string representation of an object provides no meaningful semantic data to be persisted in a user session. Other mechanisms of conversion that the middleware will try to use include custom `__str__` methods, `__dict__` attributes, `__json__` attributes, and other common mechanisms that allow for an object to be represented in such a way as to be serialized.

## Contributing

This project is open for contributions from the public. If you see any room for improvement, open an issue with your suggestion and we can discuss it.
