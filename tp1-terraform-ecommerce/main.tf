terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {
  # Configuration vide pour Windows + Docker Desktop
}

# --- VARIABLES (Pour le premier service) ---
variable "service_name" {
  description = "Nom du microservice principal"
  type        = string
  default     = "catalog"
}

variable "external_port" {
  description = "Port exposé pour le service principal"
  type        = number
  default     = 8081
}

# --- INFRASTRUCTURE COMMUNE ---
resource "docker_network" "ecommerce" {
  name = "ecommerce-net"
}

resource "docker_image" "service" {
  name         = "nginxdemos/hello:latest"
  keep_locally = true
}

# --- SERVICE 1 : CATALOGUE (Utilise les variables) ---
resource "docker_container" "service_principal" {
  name  = "${var.service_name}-service" # Donne: catalog-service
  image = docker_image.service.image_id

  networks_advanced {
    name = docker_network.ecommerce.name
  }

  ports {
    internal = 80
    external = var.external_port # Port 8081
  }

  env = [
    "SERVICE_NAME=${var.service_name}",
    "ENVIRONMENT=dev"
  ]
}

# --- SERVICE 2 : PANIER ---
# On duplique la ressource conteneur mais on change le nom et le port
resource "docker_container" "cart_service" {
  name  = "cart-service"
  image = docker_image.service.image_id # On réutilise la même image

  networks_advanced {
    name = docker_network.ecommerce.name # On se branche sur le même réseau
  }

  ports {
    internal = 80
    external = 8082 
  }

  env = [
    "SERVICE_NAME=cart",
    "ENVIRONMENT=dev"
  ]
}

# --- OUTPUTS (Pour cliquer directement) ---
output "url_catalogue" {
  value = "http://localhost:${var.external_port}"
}

output "url_panier" {
  value = "http://localhost:8082"
}