from flask import render_template, redirect, url_for, abort

from zoe_web import app
from zoe_client import ZoeClient


@app.route("/web/")
def index():
    return render_template('index.html')


@app.route("/web/status")
def web_status():
    client = ZoeClient()
    status = client.platform_status()
    return render_template('status.html', status=status)


@app.route("/web/login/<email>")
def web_login(email):
    client = ZoeClient()
    user_id = client.user_get(email)
    if user_id is None:
        user_id = client.user_new(email)
    return redirect(url_for("web_index", user_id=user_id))


@app.route("/web/<int:user_id>")
def web_index(user_id):
    client = ZoeClient()
    if not client.user_check(user_id):
        return redirect(url_for('index'))
    template_vars = {
        "user_id": user_id,
        "email": client.user_get_email(user_id)
    }
    return render_template('home.html', **template_vars)


@app.route("/web/<int:user_id>/apps")
def web_user_apps(user_id):
    client = ZoeClient()
    if not client.user_check(user_id):
        return redirect(url_for('index'))

    apps = client.spark_application_list(user_id)
    template_vars = {
        "user_id": user_id,
        "apps": apps
    }
    return render_template('apps.html', **template_vars)


@app.route("/web/<int:user_id>/spark-notebook")
def web_notebook(user_id):
    state = CAaaState()
    if not state.check_user_id(user_id):
        return redirect(url_for('index'))

    template_vars = {
        "user_id": user_id,
        "notebook_address": sm.get_notebook(user_id),
        "max_age": config.cleanup_notebooks_older_than,
        "wrn_time": int(config.cleanup_notebooks_older_than) - int(config.cleanup_notebooks_warning)
    }
    return render_template('notebook.html', **template_vars)


@app.route("/web/<int:user_id>/cluster/<int:cluster_id>/inspect")
def web_inspect(user_id, cluster_id):
    state = CAaaState()
    if not state.check_user_id(user_id):
        return redirect(url_for('index'))

    cluster = state.get_cluster(cluster_id)
    if cluster["user_id"] != user_id:
        abort(404)
    containers = state.get_containers(cluster_id=cluster_id)
    clist = []
    for cid, cinfo in containers.items():
        plist = get_container_addresses(cid)
        clist.append([cinfo["contents"], plist, cid])
    template_vars = {
        "cluster_name": cluster["name"],
        "containers": clist,
        "user_id": user_id
    }
    return render_template('inspect.html', **template_vars)


@app.route("/web/<int:user_id>/cluster/<int:cluster_id>/terminate")
def web_terminate(user_id, cluster_id):
    state = CAaaState()
    if not state.check_user_id(user_id):
        return redirect(url_for('index'))

    cluster = state.get_cluster(cluster_id)
    if cluster["user_id"] != user_id:
        abort(404)
    template_vars = {
        "cluster_name": cluster["name"],
        "cluster_id": cluster_id,
        "user_id": user_id
    }
    return render_template('terminate.html', **template_vars)


@app.route("/web/<int:user_id>/container/<int:container_id>/logs")
def web_logs(user_id, container_id):
    state = CAaaState()
    if not state.check_user_id(user_id):
        return redirect(url_for('index'))

    cont = state.get_container(container_id)
    if user_id != cont["user_id"]:
        abort(404)

    logs = sm.get_log(container_id)
    if logs is None:
        abort(404)
    else:
        logs = logs.decode("ascii")
        ret = {
            'user_id': user_id,
            'cont_contents': cont['contents'],
            "cont_logs": logs
        }
        return render_template('logs.html', **ret)


@app.route("/web/<int:user_id>/submit-spark-app")
def web_spark_submit(user_id):
    state = CAaaState()
    if not state.check_user_id(user_id):
        return redirect(url_for('index'))

    template_vars = {
        'user_id': user_id,
    }
    return render_template('submit.html', **template_vars)
