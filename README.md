# Akamai Cloud Marketplace Cluster Apps

The Akamai Cloud Marketplace is designed to make it easier for developers and companies to share [One-Click Clusters](https://www.linode.com/marketplace/) with the Linode community. One-Click Cluster apps are modular solutioning tools written as Ansible playbooks. This allows users to quickly deploy services and perform essential configurations on a Akamai compute instance's post boot sequence.

A Marketplace deployment refers to an application (single service on a single node) or a cluster (multi-node clustered service such as Galera). A combination of Linode [StackScripts](https://techdocs.akamai.com/cloud-computing/docs/stackscripts) and Ansible playbooks give the Marketplace a one-click installation and delivery mechanism for deployments. The end user is billed just for the underlying cloud resources (compute instances, storage volumes, etc) in addition to any applicable BYOLs.

## Marketplace App Development Guidelines.

A Marketplace application consists of three major components:

- [Stackscript](#Stackscript) 
- [Ansible Playbook](#Ansible-Playbook)
- A public GIT repository to clone from

### Stackscript

A [Stackscript](https://techdocs.akamai.com/cloud-computing/docs/write-a-custom-script-for-use-with-stackscripts) is a Bash script that is stored on Linode hosts and is accessible to all customers. When an instance is booted, the Stackscript is executed to initiate the provisioning process.

### Ansible Playbook

All Ansible playbooks should generally adhere to the [sample directory layout](https://docs.ansible.com/ansible/latest/user_guide/sample_setup.html#sample-ansible-setup) and best practices/recommendations from the latest Ansible [User Guide](https://docs.ansible.com/ansible/latest/user_guide/index.html).

### Helper Functions

Helper functions are static roles that can be called at will when we are trying to accomplish a repeatable system task. Instead of rewriting the same function for multiple One-Click Apps, we can simply import the helper role to accomplish the same effect. This results in basic system configurations being performed predictably and reliably, without the variance of individual authors.

More detailed information on the available helper functions and variables can be found in the [linode_helpers](apps/linode_helpers/README.md) root directory.

For more information on roles please refer to the [Ansible documentation](https://docs.ansible.com/ansible/latest/user_guide/playbooks_reuse_roles.html#using-roles-at-the-play-level).

### Anatomy of Cluster Deployments

All Akamai Cloud Marketplace applications leverage the use of [Stackscripts](#Stackscript) to perform the configuration of the app. The sequence of events follow for:

- The deployment Stackscript gathers the necessary information from the user. Variables are captured from the Cloud Manager as UDF fields
- The UDF fields are exported to the instance as local variables
- The Ansible playbook is pulled down for the deployment from Github
- Ansible configures the instance

Clustered applications, referred to as One-Click clusters, utilizes Linode's Ansible collection to configure and provision new instances for the clustered application.

At the root of every application, the `provision.yml` is responsible for initial provisioning process. This is run by the first instance that is created on the cluster which typically is referred to as the provisioner instance. The provisioner deploys new instances, get information about the instances via API and building the correct data structure which can be iterated later in the playbook.

The `site.yml` contains your typical Ansible playbook to configure the stack against the hosts in the `hosts` file. In the event that a deployment fails, the `destroy.yml` is triggered and all instances except the provisioner node are destroyed. This allows the user to analyze the `/var/log/stackscript.log` for the failure.


## Creating Your Own

For more information on creating and submitting a Partner App for the Akamai Cloud Marketplace please see [Contributing](docs/CONTRIBUTING.md) and [Development](docs/DEVELOPMENT.md).
