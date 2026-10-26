terraform {
  required_version = ">= 1.6"
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.48"
    }
  }
}

variable "hcloud_token" {
  description = "Jeton API Hetzner Cloud (à fournir par variable d'environnement TF_VAR_hcloud_token)"
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "Clé publique SSH autorisée sur le serveur"
  type        = string
}

variable "admin_cidr" {
  description = "Plage IP autorisée pour SSH (ex. 203.0.113.4/32)"
  type        = string
}

provider "hcloud" {
  token = var.hcloud_token
}

resource "hcloud_ssh_key" "deploy" {
  name       = "shortener-deploy"
  public_key = var.ssh_public_key
}

resource "hcloud_firewall" "shortener" {
  name = "shortener"

  rule {
    description = "SSH depuis l'administrateur uniquement"
    direction   = "in"
    protocol    = "tcp"
    port        = "22"
    source_ips  = [var.admin_cidr]
  }
  rule {
    description = "HTTP"
    direction   = "in"
    protocol    = "tcp"
    port        = "80"
    source_ips  = ["0.0.0.0/0", "::/0"]
  }
  rule {
    description = "HTTPS"
    direction   = "in"
    protocol    = "tcp"
    port        = "443"
    source_ips  = ["0.0.0.0/0", "::/0"]
  }
}

resource "hcloud_server" "shortener" {
  name         = "shortener"
  server_type  = "cx22"
  image        = "debian-12"
  location     = "nbg1"
  ssh_keys     = [hcloud_ssh_key.deploy.id]
  firewall_ids = [hcloud_firewall.shortener.id]
}

output "server_ip" {
  description = "Adresse à mettre dans l'inventaire Ansible"
  value       = hcloud_server.shortener.ipv4_address
}
