""" jsonp transport """
import uuid
from gevent.queue import Empty
from pyramid.compat import url_unquote
from pyramid_sockjs.protocol import OPEN, HEARTBEAT
from pyramid_sockjs.protocol import encode, decode, close_frame, message_frame


def JSONPolling(session, request):
    meth = request.method
    response = request.response
    response.headers['Content-Type'] = 'application/javascript; charset=UTF-8'

    if session.is_new():
        callback = request.GET.get('c', None)
        if callback is None:
            raise Exception('"callback" parameter is required')

        response.text = '%s("o");' % callback
        session.open()
        session.manager.release(session)

    elif meth == "GET":
        callback = request.GET.get('c', None)
        if callback is None:
            raise Exception('"callback" parameter is required')

        try:
            message = session.get_transport_message(timeout=5.0)
        except Empty:
            message = HEARTBEAT
            session.heartbeat()
        else:
            message = message_frame(message)
        response.text = "%s(%s);"%(callback, encode(message))
        session.manager.release(session)

    elif meth == "POST":
        data = request.body_file.read()

        ctype = request.headers.get('Content-Type', '').lower()
        if ctype == 'application/x-www-form-urlencoded':
            if not data.startswith('d='):
                raise Exception("Payload expected.")

        data = url_unquote(data[2:])

        messages = decode(data)
        for msg in messages:
            session.message(msg)

        response.status = 200
        response.headers['Content-Type'] = 'text/plain; charset=UTF-8'
        response.body = 'ok'
    else:
        raise Exception("No support for such method: %s"%meth)

    return response
