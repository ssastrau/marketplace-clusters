# Akamai Cloud Marketplace Cluster Functions

This directory contains a list of helper roles that can be imported via Ansible when clustered applications are being provisioned. This allows us to use commonly-used and repetitive tasks as modules similarly to how functions work in programming.

## Helper Functions

| Name | Description |
| :--- | :---        |
| certbot_ssl | Generates and sets auto-renew for Let's Encrypt certificates. More information on usage see [below](#Certbot-SSL) |
| remove_provision_keys | Removes any keys created by the provisioner to create the cluster. If `DEBUG` is present as a variable during runtime, keys are not removed to allow further deployment debugging. |
| securessh | Perform SSH hardening by updating `/etc/ssh/sshd_config` file  to prevent password authentication and enable public key authentication for all users, including root. |
| setdomain | Sets the `_domain` variable for configuring SSL certificates on a public facing HTTP endpoint. This is used in conjunction with the `certbot_ssl` module to create valid Let's Encrypt certificates |
| setrootpwd | Sets the root password provided in Cloud Manager to all cluster instances. |
| sshkey | Copies over the provided SSH keys from Cloud manager to all cluster instances. |
| sudouser | Creates a limited sudo user on the system. Validation is performed to ensure that the provided username is not already present in the system. |
| ufw | Installs UFW as the backend instance firewall. |
| update_pkgs | Updates and upgrades all packages on the system. This typically found in the initial provisioning process of the instance. |

### Certbot SSL

Generates and sets auto-renew for Let's Encrypt certificates. This helper allows us to configure SSL for a web HTTP endpoint in a clustered environment. When using this helper, the task must include the following variables: 
- `host`
- `webserver_task`

This is an example of what a task will look like. Where `host` is the server that has the HTTP endpoint.

Example:
```yaml
- name: Configuring SSL on {{ _domain }}
    import_role:
      name: certbot_ssl
    vars:
      host: "{{ groups['provisioner'][0] }}"
      webserver_stack: lemp
```

## Creating Your Own

Additional Linode Helpers can be added while respecting [Ansible common practice](https://docs.ansible.com/ansible/2.8/user_guide/playbooks_best_practices.html) and directory structure. Linode Helpers should perform common, repeatable system configuration tasks with minimal dependencies. Linode Helper functions can be imported as roles as needed in playbooks. Please see [DEVELOPMENT.md](docs/DEVELOPMENT.md) for more detailed standards.