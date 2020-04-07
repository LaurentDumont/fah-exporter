# Standard imports
from prometheus_client import start_http_server, Metric, REGISTRY
import time
import subprocess
import re
import json
import os
import multiprocessing
from functools import partial

# {
#    "id": "00",
#    "status": "RUNNING",
#    "description": "cpu:5",
#    "options": {"idle": "false", "paused": "false"},
#    "reason": "",
#    "idle": False
# }
#
# {
#    "id": "01",
#    "status": "READY",
#    "description": "gpu:0:GP104 [GeForce GTX 1070] 6463",
#    "options": {
#        "idle": "false",
#        "paused": "false"
#    },
#    "reason": "",
#    "idle": false
# }


def get_fah_output(info_type, target):

    if info_type == "queues":
        command = "queue-info"
        regex = r'PyON 1 units((?:.*\r?\n?)*)---'

    if info_type == "slots":
        command = "slot-info"
        regex = r'PyON 1 slots((?:.*\r?\n?)*)---'
    fah_command = generate_fah_command(target, command)
    command_result = subprocess.run([fah_command], shell=True,
                                    capture_output=True, text=True, timeout=20)
    raw_text = command_result.stdout
    filtered_text = re.search(regex, raw_text)
    pyon = filtered_text.groups()[0].replace("False", "false")
    # To get this compatible with json - we need lowercase true and false
    json_compatible = pyon.replace("True", "true")

    fah_json = json.loads(json_compatible)
    worker_json = {'worker_name': target}
    for data in fah_json:
        data.update(worker_json)

    return fah_json


def thread_fah_requests(targets, info_type):
    process_pool = multiprocessing.Pool(multiprocessing.cpu_count())
    partial_function = partial(get_fah_output, info_type)
    json_data = process_pool.map(partial_function, targets)
    process_pool.close()
    return json_data


def generate_fah_command(client, command):
    fah_command = """
nc {} 36330 <<EOF
{}
exit
EOF
""".format(client, command)
    return fah_command


# Convert the status into a numerical value.
# Return the numerical value if found, 666 if no matches.
def convert_fah_status(status):
    status_map = {'READY': 0,
                  'RUNNING': 1,
                  'IDLE': 3,
                  'DOWNLOAD': 4, }
    return status_map.get(status, 666)


class FahCollector(object):
    def __init__(self):
        self._endpoint = '6666'

    def collect(self):
        # List of IPs of FAH clients that need to be queries.
        fah_clients = os.getenv('FAH_CLIENTS').split(',')
        fah_slot_metric = Metric(
            'fah_slot_info', 'FAH work slot info', 'gauge')
        fah_job_credit = Metric(
            'fah_job_credit', 'FAH job credit estimate', 'gauge')
        fah_job_progress = Metric(
            'fah_job_progress', 'FAH job percentage progress', 'gauge')
        fah_job_status = Metric(
            'fah_job_status', 'FAH job status', 'gauge')

        info_type = "slots"
        json_data = thread_fah_requests(fah_clients, info_type)
        for data in json_data:
            for slot in data:
                fah_slot_metric.add_sample('fah_slot_info', value=convert_fah_status(slot['status']), labels={
                    'slot_id': str(slot['id']),
                    'description': str(slot['description']),
                    'fah_worker': str(slot['worker_name']),
                })
        info_type = "queues"
        json_data = thread_fah_requests(fah_clients, info_type)
        for data in json_data:
            for job in data:
                fah_job_status.add_sample('fah_job_status', value=convert_fah_status(job['state']), labels={
                    'project': str(job['project']),
                    'percentdone': str(job['percentdone'].replace('%', '')),
                    'waitingon': str(job['waitingon']),
                    'fah_worker': str(job['worker_name']),
                })
                fah_job_credit.add_sample('fah_job_credit', value=job['creditestimate'], labels={
                    'id': str(job['id']),
                    'fah_worker': str(job['worker_name']),
                })

        yield fah_slot_metric
        yield fah_job_status
        yield fah_job_credit


if __name__ == '__main__':
    start_http_server(6666)
    REGISTRY.register(FahCollector())
    while True:
        time.sleep(30)
