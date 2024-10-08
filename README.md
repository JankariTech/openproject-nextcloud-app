# OpenProject as Nextcloud's External App

## Manual Installation
For the manual installation of `OpenProject` as an external application of `Nextcloud`, make sure that your `Nextcloud` as well as `OpenProject` instance is up and running.

### 1. Install `app_api` application

Assuming you’re in the apps folder directory:

- Clone
	```bash
	git clone https://github.com/nextcloud/app_api.git
	```
- build
   ```bash
   cd app_api
   npm ci && npm run dev
    ```
- Enable the `app_api`
	```bash
	# Assuming you’re in nextcloud server root directory
	sudo -u www-data php occ a:e app_api
	```
 
### 2. Register deploy daemons (In Nextcloud)

- Navigate to `Administration Settings > AppAPI`
- Click `Register Daemon`
- Select `Manual Install` for Daemon configuration template
- Put `manual_install` for name and display name
- Deployment method as `manual-install`
- Daemon host as `localhost`
- Click Register

### 3. Running OpenProject locally
Set up and build `OpenProject` locally following [OpenProject Development Setup](https://www.openproject.org/docs/development/development-environment/)
After the setup, run `OpenProject` locally with the given command line.

>NOTE: If you are running Nextcloud in a sub folder  replace `NC_SUB_FOLDER` with the path name, otherwise remove it.

```bash
# the reason to set relative path with NC_SUB_FOLDER is it makes easy to change when there is redirection url in response
OPENPROJECT_RAILS__RELATIVE__URL__ROOT=/<NC_SUB_FOLDER>/index.php/apps/app_api/proxy/openproject-nextcloud-app \
foreman start -f Procfile.dev
```

### 4. Configure and Run External `openproject-nextcloud-app` application
Assuming you’re in the apps folder directory:

- Clone
  ```bash
  git clone https://github.com/JankariTech/openproject-nextcloud-app.git
  ```
- Configure script before running external app
   ```bash
	 cd openproject-nextcloud-app
	 cp ex_app_run_script.sh.example ex_app_run_script.sh
    ```
  Once you have copied the script to run the external application, configure the following environments

  - `APP_ID` is the application id of the external app
  - `APP_PORT` is port for the external app
  - `APP_HOST` is the host for the external app
  - `APP_VERSION` is the version of external app
  - `APP_SECRET`  is a secret key used by Nextcloud to authenticate with external applications. Administrators can set any secret, but they must ensure that the same secret is used when both registering and running the external application.
  - `AA_VERSION` indicates the version of app `app_api`. The external application needs this information because `app_api` is responsible for handling tasks like registration, authentication, and managing external apps. To see the version of `app_api`, list apps from the root directory of server with the command.
    ```bash
    sudo -u www-data php occ a:l
    ```
  - `EX_APP_VERSION` is the version of the external application and must be same as `APP_VERSION`
  - `EX_APP_ID` is the version of the external application and must be same as `APP_ID`
  - `NC_SUB_FOLDER` is the subfolder in which nextcloud is running (make sure to use same in OPENPROJECT_RAILS__RELATIVE__URL__ROOT while running openproject)
  - `OP_BACKEND_URL` is the url in which `OpenProject` is up and running
  - `NEXTCLOUD_URL` the url in which `Nextcloud` is up and running

    >***NOTE:***  In the given environments, `APP_ID`, `APP_PORT`, `APP_HOST`, and `APP_VERSION` are used to run the external application, while `APP_SECRET`, `EX_APP_VERSION`, `EX_APP_ID`, and `AA_VERSION` are needed for the external app and Nextcloud to authenticate each other.

- Install required Python packages to run external application `openproject-nextcloud-app`
	```bash
	# Make sure that you have python3 installed in your local system
	python3 -m pip install -r requirements.txt
	```

- Run external application with the script
   ```bash
   bash ex_app_run_script.sh
    ```

### 5. Register and deploy external application `openproject-nextcloud-app` in Nextcloud's external apps

Assuming you’re in nextcloud server root directory

- Register and deploy external application `openproject-nextcloud-app`
  ```bash
  sudo -u www-data php occ app_api:app:register openproject-nextcloud-app manual_install --json-info \
    "{\"id\":\"<EX_APP_ID>\",
  	\"name\":\"<EX_APP_ID>\",
  	\"daemon_config_name\":\"manual_install\",
  	\"version\":\"<EX_APP_VERSION>\",
  	\"secret\":\"<APP_SECRET>\",
  	\"scopes\":[\"ALL\"],
  	\"port\":<APP_PORT>,
  	\"routes\": [{\"url\":\".*\",\"verb\":\"GET, POST, PUT, DELETE, HEAD, PATCH, OPTIONS, TRACE\",
  	\"access_level\":1,
  	\"headers_to_exclude\":[]}]}" \
    --force-scopes --wait-finish
  ```
  In the above bash command use the same value for `EX_APP_ID`, `EX_APP_VERSION`, `APP_SECRET`, and `APP_PORT` as used while running external app `openproject-nextcloud-app`


Now OpenProject can be reached on:
```bash
http://${APP_HOST}/${NC_SUB_FOLDER}/index.php/apps/app_api/proxy/openproject-nextcloud-app
```

