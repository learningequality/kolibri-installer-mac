import json
import os
import subprocess
from datetime import datetime

kolibri_dir = os.path.abspath(os.path.join('src', 'kolibri'))


def kolibri_version():
    """
    Returns the major.minor version of Kolibri if it exists
    """
    with open(os.path.join(kolibri_dir, 'VERSION'), 'r') as version_file:
        # p4a only likes digits and decimals
        return version_file.read().strip()


def commit_hash():
    """
    Returns the number of commits of the Kolibri Android repo. Returns 0 if something fails.

    TODO hash, unless there's a tag. Use alias to annotate
    """
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    p = subprocess.Popen(
        "git rev-parse --short HEAD",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        cwd=repo_dir,
        universal_newlines=True
    )
    return p.communicate()[0].rstrip()


def git_tag():
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    p = subprocess.Popen(
        "git tag --points-at {}".format(commit_hash()),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        cwd=repo_dir,
        universal_newlines=True
    )
    return p.communicate()[0].rstrip()


def build_type():
    key_alias = os.getenv('P4A_RELEASE_KEYALIAS', 'unknown')
    if key_alias == 'LE_DEV_KEY':
        return 'dev'
    if key_alias == 'LE_RELEASE_KEY':
        return 'official'
    return key_alias


def apk_version():
    """
    Returns the version to be used for the Kolibri Android app.
    Schema: [kolibri version]-[android installer version or githash]-[build signature type]
    """
    android_version_indicator = git_tag() or commit_hash()
    return '{}-{}-{}'.format(kolibri_version(), android_version_indicator, build_type())


def android_build_number():
    """
    Returns the build number for the apk. This is the mechanism used to understand whether one
    build is newer than another. Uses buildkite build number with time as local dev backup
    """

    # Patch, due to a build error.
    # Envar was not being passed into the container this runs in, and the
    # build submitted to the play store ended up using the dev build number.
    # We can't go backwards. So we're adding to the one submitted at first.
    build_base_number = 2009000000

    buildkite_build_number = os.getenv('BUILDKITE_BUILD_NUMBER')

    print('--- Assigning Build Number')

    if buildkite_build_number is not None:
        build_number = build_base_number + int(buildkite_build_number)
        print(build_number)
        return str(build_number)

    print('Buildkite build # not found, using dev alternative')
    alt_build_number = datetime.now().strftime('%y%m%d%H%M')
    print(alt_build_number)
    return alt_build_number


def build_number():
    """
    Returns the build number for the apk. This is the mechanism used to understand whether one
    build is newer than another. Uses buildkite build number with time as local dev backup
    """
    return os.getenv('BUILDKITE_BUILD_NUMBER', datetime.now().strftime('%y%m%d%H%M'))


def get_env_with_version_set(args):
    env = os.environ.copy()

    build_num = build_number()
    if 'android' in args:
        build_num = android_build_number()

    env['KOLIBRI_VERSION'] = kolibri_version()
    env['APP_BUILD_NUMBER'] = build_num

    # set version information, Android appends more info to the version string
    if 'android' in args:
        env['FULL_VERSION'] = apk_version()
    else:
        # TODO: Determine if there's a better place to store the app version info.
        # Maybe it makes sense to have a kolibri_app module with everything except
        # the main.py code in it?
        info_json = json.load(open(os.path.join(os.getcwd(), 'project_info.json')))
        env['FULL_VERSION'] = info_json['app_version']
    return env
