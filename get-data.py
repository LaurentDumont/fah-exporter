import subprocess
import re
import json
import multiprocessing

command = """
nc 10.200.10.101 36330 <<EOF
queue-info
exit
EOF
"""


def get_fah_data(target):
    command_result = subprocess.run([command], shell=True,
                                    capture_output=True, text=True, timeout=15)
    raw_text = command_result.stdout
    filtered_text = re.search(r'PyON 1 units((?:.*\r?\n?)*)---', raw_text)

    pyon_data = filtered_text.groups()[0].replace("False", "false")
    json_compatible_data = pyon_data.replace("True", "true")

    json_data = json.loads(json_compatible_data)
    return json_data


if __name__ == '__main__':
    targets = ['10.200.10.101', '10.200.10.101']
    p = multiprocessing.Pool(multiprocessing.cpu_count())
    test = p.map(get_fah_data, targets)
    print(test)
