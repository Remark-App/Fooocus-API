import argparse
import os
import re
import shutil
import subprocess
import sys
from importlib.util import find_spec
from threading import Thread

from fooocus_api_version import version
from fooocusapi.repositories_versions import fooocus_commit_hash

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

python = sys.executable
default_command_live = True
index_url = os.environ.get('INDEX_URL', "")
re_requirement = re.compile(r"\s*([-_a-zA-Z0-9]+)\s*(?:==\s*([-+_.a-zA-Z0-9]+))?\s*")

fooocus_name = 'Fooocus'

modules_path = os.path.dirname(os.path.realpath(__file__))
script_path = modules_path
dir_repos = "repositories"


# This function was copied from [Fooocus](https://github.com/lllyasviel/Fooocus) repository.
def onerror(func, path, exc_info):
    import stat
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise 'Failed to invoke "shutil.rmtree", git management failed.'


# This function was copied from [Fooocus](https://github.com/lllyasviel/Fooocus) repository.
def git_clone(url, dir, name, hash=None):
    import pygit2

    try:
        try:
            repo = pygit2.Repository(dir)
            remote_url = repo.remotes['origin'].url
            if remote_url != url:
                print(f'{name} exists but remote URL will be updated.')
                del repo
                raise url
            else:
                print(f'{name} exists and URL is correct.')
        except:
            if os.path.isdir(dir) or os.path.exists(dir):
                shutil.rmtree(dir, onerror=onerror)
            os.makedirs(dir, exist_ok=True)
            repo = pygit2.clone_repository(url, dir)
            print(f'{name} cloned from {url}.')

        remote = repo.remotes['origin']
        remote.fetch()

        commit = repo.get(hash)

        repo.checkout_tree(commit, strategy=pygit2.GIT_CHECKOUT_FORCE)
        repo.set_head(commit.id)

        print(f'{name} checkout finished for {hash}.')
    except Exception as e:
        print(f'Git clone failed for {name}: {str(e)}')


# This function was copied from [Fooocus](https://github.com/lllyasviel/Fooocus) repository.
def repo_dir(name):
    return os.path.join(script_path, dir_repos, name)


# This function was copied from [Fooocus](https://github.com/lllyasviel/Fooocus) repository.
def run(command, desc=None, errdesc=None, custom_env=None, live: bool = default_command_live) -> str:
    if desc is not None:
        print(desc)

    run_kwargs = {
        "args": command,
        "shell": True,
        "env": os.environ if custom_env is None else custom_env,
        "encoding": 'utf8',
        "errors": 'ignore',
    }

    if not live:
        run_kwargs["stdout"] = run_kwargs["stderr"] = subprocess.PIPE

    result = subprocess.run(**run_kwargs)

    if result.returncode != 0:
        error_bits = [
            f"{errdesc or 'Error running command'}.",
            f"Command: {command}",
            f"Error code: {result.returncode}",
        ]
        if result.stdout:
            error_bits.append(f"stdout: {result.stdout}")
        if result.stderr:
            error_bits.append(f"stderr: {result.stderr}")
        raise RuntimeError("\n".join(error_bits))

    return (result.stdout or "")


# This function was copied from [Fooocus](https://github.com/lllyasviel/Fooocus) repository.
def run_pip(command, desc=None, live=default_command_live):
    try:
        index_url_line = f' --index-url {index_url}' if index_url != '' else ''
        return run(f'"{python}" -m pip {command} --prefer-binary{index_url_line}', desc=f"Installing {desc}",
                   errdesc=f"Couldn't install {desc}", live=live)
    except Exception as e:
        print(e)
        print(f'CMD Failed {desc}: {command}')
        return None



# This function was copied from [Fooocus](https://github.com/lllyasviel/Fooocus) repository.
def requirements_met(requirements_file):
    """
    Does a simple parse of a requirements.txt file to determine if all rerqirements in it
    are already installed. Returns True if so, False if not installed or parsing fails.
    """

    import importlib.metadata
    import packaging.version

    with open(requirements_file, "r", encoding="utf8") as file:
        for line in file:
            if line.strip() == "":
                continue

            m = re.match(re_requirement, line)
            if m is None:
                return False

            package = m.group(1).strip()
            version_required = (m.group(2) or "").strip()

            if version_required == "":
                continue

            try:
                version_installed = importlib.metadata.version(package)
            except Exception:
                return False

            if packaging.version.parse(version_required) != packaging.version.parse(version_installed):
                return False

    return True


def download_repositories():
    import pygit2

    pygit2.option(pygit2.GIT_OPT_SET_OWNER_VALIDATION, 0)

    http_proxy = os.environ.get('HTTP_PROXY')
    https_proxy = os.environ.get('HTTPS_PROXY')
    
    if http_proxy != None:
        print(f"Using http proxy for git clone: {http_proxy}")
        os.environ['http_proxy'] = http_proxy

    if https_proxy != None:
        print(f"Using https proxy for git clone: {https_proxy}")
        os.environ['https_proxy'] = https_proxy

    # Check and download Fooocus
    fooocus_repo = os.environ.get(
        'FOOOCUS_REPO', 'https://github.com/lllyasviel/Fooocus')
    git_clone(fooocus_repo, repo_dir(fooocus_name),
              "Fooocus", fooocus_commit_hash)
    

def is_installed(package):
    try:
        spec = find_spec(package)
    except ModuleNotFoundError:
        return False

    return spec is not None


def download_models():
    vae_approx_filenames = [
        ('xlvaeapp.pth', 'https://huggingface.co/lllyasviel/misc/resolve/main/xlvaeapp.pth'),
        ('vaeapp_sd15.pth', 'https://huggingface.co/lllyasviel/misc/resolve/main/vaeapp_sd15.pt'),
        ('xl-to-v1_interposer-v3.1.safetensors',
        'https://huggingface.co/lllyasviel/misc/resolve/main/xl-to-v1_interposer-v3.1.safetensors')
    ]

    from modules.model_loader import load_file_from_url
    from modules.config import path_checkpoints as modelfile_path, path_loras as lorafile_path,path_vae_approx as vae_approx_path,path_fooocus_expansion as fooocus_expansion_path, \
        checkpoint_downloads, path_embeddings as embeddings_path, embeddings_downloads, lora_downloads

    for file_name, url in checkpoint_downloads.items():
        load_file_from_url(url=url, model_dir=modelfile_path, file_name=file_name)
    for file_name, url in embeddings_downloads.items():
        load_file_from_url(url=url, model_dir=embeddings_path, file_name=file_name)
    for file_name, url in lora_downloads.items():
        load_file_from_url(url=url, model_dir=lorafile_path, file_name=file_name)
    for file_name, url in vae_approx_filenames:
        load_file_from_url(url=url, model_dir=vae_approx_path, file_name=file_name)

    load_file_from_url(
        url='https://huggingface.co/lllyasviel/misc/resolve/main/fooocus_expansion.bin',
        model_dir=fooocus_expansion_path,
        file_name='pytorch_model.bin'
    )


def prepare_environments(args) -> bool:
    if not args.skip_pip:
        torch_index_url = os.environ.get('TORCH_INDEX_URL', "https://download.pytorch.org/whl/cu121")
        
        # Check if need pip install
        requirements_file = 'requirements.txt'
        if not requirements_met(requirements_file):
            run_pip(f"install -r \"{requirements_file}\"", "requirements")

        if not is_installed("torch") or not is_installed("torchvision"):
            print(f"torch_index_url: {torch_index_url}")
            run_pip(f"install torch==2.0.1 torchvision==0.15.2 --extra-index-url {torch_index_url}", "torch")

    skip_sync_repo = False
    if args.sync_repo is not None:
        if args.sync_repo == 'only':
            print("Only download and sync depent repositories")
            download_repositories()
            models_path = os.path.join(
                script_path, dir_repos, fooocus_name, "models")
            print(
                f"Sync repositories successful. Now you can put model files in subdirectories of '{models_path}'")
            return False
        elif args.sync_repo == 'skip':
            skip_sync_repo = True
        else:
            print(
                f"Invalid value for argument '--sync-repo', acceptable value are 'skip' and 'only'")
            exit(1)

    if not skip_sync_repo:
        download_repositories()

    import fooocusapi.worker as worker
    worker.task_queue.queue_size = args.queue_size
    worker.task_queue.history_size = args.queue_history

    if args.base_url is None or len(args.base_url.strip()) == 0:
        host = args.host
        if host == '0.0.0.0':
            host = '127.0.0.1'
        args.base_url = f"http://{host}:{args.port}"

    # Add dependent repositories to import path
    sys.path.append(script_path)
    fooocus_path = os.path.join(script_path, dir_repos, fooocus_name)
    sys.path.insert(0, fooocus_path) # need add __init__.py in folder "modules"
    backend_path = os.path.join(fooocus_path, 'backend', 'headless')
    if backend_path not in sys.path:
        sys.path.append(backend_path)
    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

    sys.argv = [sys.argv[0]]

    if args.disable_private_log:
        sys.argv.append('--disable-image-log')

    if args.preset is not None:
        # Remove and copy preset folder
        origin_preset_folder = os.path.abspath(os.path.join(script_path, dir_repos, fooocus_name, 'presets'))
        preset_folder = os.path.abspath(os.path.join(script_path, 'presets'))
        if os.path.exists(preset_folder):
            shutil.rmtree(preset_folder)
        shutil.copytree(origin_preset_folder, preset_folder)

        sys.argv.append('--preset')
        sys.argv.append(args.preset)
    import modules.config as config
    import modules.flags as flags
    import fooocusapi.parameters as parameters
    parameters.default_inpaint_engine_version = config.default_inpaint_engine_version
    parameters.defualt_styles = config.default_styles
    parameters.default_base_model_name = config.default_base_model_name
    parameters.default_refiner_model_name = config.default_refiner_model_name
    parameters.default_refiner_switch = config.default_refiner_switch
    parameters.default_loras = config.default_loras
    parameters.default_cfg_scale = config.default_cfg_scale
    parameters.default_prompt_negative = config.default_prompt_negative
    parameters.default_aspect_ratio = parameters.get_aspect_ratio_value(config.default_aspect_ratio)
    parameters.available_aspect_ratios = [parameters.get_aspect_ratio_value(a) for a in config.available_aspect_ratios]

    ini_cbh_args()

    #download_models()

    if args.preload_pipeline:
        preplaod_pipeline()

    return True

def pre_setup(skip_sync_repo: bool=False, disable_private_log: bool=False, skip_pip=False, load_all_models: bool=False, preload_pipeline: bool=False, preset: str | None=None):
    class Args(object):
        host = '127.0.0.1'
        port = 8888
        base_url = None
        sync_repo = None
        disable_private_log = False
        skip_pip = False
        preload_pipeline = False
        queue_size = 3
        queue_history = 100
        preset = None

    print("[Pre Setup] Prepare environments")

    args = Args()
    args.disable_private_log = disable_private_log
    args.preload_pipeline = preload_pipeline
    args.preset = preset
    if skip_sync_repo:
        args.sync_repo = 'skip'
    prepare_environments(args)

    if load_all_models:
        import modules.config as config
        from fooocusapi.parameters import default_inpaint_engine_version
        config.downloading_upscale_model()
        config.downloading_inpaint_models(default_inpaint_engine_version)
        config.downloading_controlnet_canny()
        config.downloading_controlnet_cpds()
        config.downloading_ip_adapters()
    print("[Pre Setup] Finished")


# This function was copied from [Fooocus](https://github.com/lllyasviel/Fooocus) repository.
def ini_cbh_args():
    from args_manager import args
    return args


def preplaod_pipeline():
    print("Preload pipeline")
    import modules.default_pipeline as _


if __name__ == "__main__":
    print(f"Python {sys.version}")
    print(f"Fooocus-API version: {version}")

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8888,
                        help="Set the listen port, default: 8888")
    parser.add_argument("--host", type=str,
                        default='127.0.0.1', help="Set the listen host, default: 127.0.0.1")
    parser.add_argument("--base-url", type=str, default=None, help="Set base url for outside visit, default is http://host:port")
    parser.add_argument("--log-level", type=str,
                        default='info', help="Log info for Uvicorn, default: info")
    parser.add_argument("--sync-repo", default=None,
                        help="Sync dependent git repositories to local, 'skip' for skip sync action, 'only' for only do the sync action and not launch app")
    parser.add_argument("--disable-private-log", default=False, action="store_true", help="Disable Fooocus image log, won't save output files (include generated image files)")
    parser.add_argument("--skip-pip", default=False, action="store_true", help="Skip automatic pip install when setup")
    parser.add_argument("--preload-pipeline", default=False, action="store_true", help="Preload pipeline before start http server")
    parser.add_argument("--queue-size", type=int, default=3, help="Working queue size, default: 3, generation requests exceeding working queue size will return failure")
    parser.add_argument("--queue-history", type=int, default=100, help="Finished jobs reserve in memory size, default: 100")
    parser.add_argument("--preset", type=str, default=None, help="Apply specified UI preset.")


    args = parser.parse_args()

    prepare_environments(args)
