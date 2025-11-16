param(
    [Parameter(Position=0)]
    [string]$Command = "help",

    [Parameter(Position=1, ValueFromRemainingArguments=$true)]
    [string[]]$Args
)

function Show-Help {
    Write-Host "Available commands:" -ForegroundColor Green
    Write-Host ""
    Write-Host "Docker commands:" -ForegroundColor Yellow
    Write-Host "  .\run.ps1 build              - Build Docker images"
    Write-Host "  .\run.ps1 up                 - Start services"
    Write-Host "  .\run.ps1 down               - Stop containers"
    Write-Host "  .\run.ps1 restart            - Restart all services"
    Write-Host "  .\run.ps1 logs               - Show logs"
    Write-Host "  .\run.ps1 shell              - Open shell in container"
    Write-Host "  .\run.ps1 clean              - Remove containers and volumes"
    Write-Host "  .\run.ps1 edit [filename]    - Run editor in Docker"
    Write-Host ""
    Write-Host "Local commands:" -ForegroundColor Yellow
    Write-Host "  .\run.ps1 install-local      - Install Python dependencies"
    Write-Host "  .\run.ps1 run-local [file]   - Run editor locally"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 edit                    # New file"
    Write-Host "  .\run.ps1 edit myfile.txt         # Open specific file"
    Write-Host "  .\run.ps1 run-local notes.txt     # Run locally"
}

switch ($Command.ToLower()) {
    "help" {
        Show-Help
    }
    "build" {
        docker compose build
    }
    "up" {
        docker compose up -d
    }
    "down" {
        docker compose down
    }
    "restart" {
        docker compose down
        docker compose up -d
    }
    "logs" {
        docker compose logs -f
    }
    "shell" {
        docker compose exec app /bin/sh
    }
    "clean" {
        docker compose down -v --rmi local
        Write-Host "Cleaned up containers, volumes, and images" -ForegroundColor Green
    }
    "test" {
        docker compose run --rm app python -c "import textual; import httpx; print('Dependencies OK')"
    }
    "edit" {
        if ($Args) {
            docker compose run --rm app python txtarea.py $Args
        } else {
            docker compose run --rm app python txtarea.py
        }
    }
    "install-local" {
        pip install -r requirements.txt
        Write-Host "Dependencies installed locally" -ForegroundColor Green
    }
    "run-local" {
        if ($Args) {
            python txtarea.py $Args
        } else {
            python txtarea.py
        }
    }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host ""
        Show-Help
    }
}