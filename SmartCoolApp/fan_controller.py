"""
Fan Controller Module - Monster Telemetria
Permite controlo e monitorização de velocidade das ventoinhas de CPU e GPU:
- Modos pré-definidos: Silencioso, Equilibrado, Gaming, Turbo Máximo (100%), Automático
- Sliders manuais de velocidade percentual (20% a 100%)
- Interface nativa com NVML (nvml.dll) para GPUs NVIDIA GeForce / RTX
- Cálculo e simulação de rotações por minuto (RPM) e perfis térmicos
"""

import os
import ctypes

class FanController:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # Estado das Ventoinhas
        self.cpu_fan_auto = True
        self.gpu_fan_auto = True
        self.cpu_fan_target = 65  # %
        self.gpu_fan_target = 60  # %
        
        # Limites estimados de RPM
        self.cpu_min_rpm = 650
        self.cpu_max_rpm = 2500
        self.gpu_min_rpm = 0
        self.gpu_max_rpm = 2900

        # Tentativa de inicialização do NVML para controlo direto da GPU NVIDIA
        self.nvml = None
        self.nvml_device = None
        self.can_control_gpu_hardware = False
        self._init_nvml()

    def _init_nvml(self):
        """Tenta ligar à biblioteca nvml.dll da NVIDIA."""
        try:
            self.nvml = ctypes.CDLL("nvml.dll")
            if self.nvml.nvmlInit_v2() == 0:
                dev = ctypes.c_void_p()
                if self.nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(dev)) == 0:
                    self.nvml_device = dev
                    # Testar permissões de escrita de velocidade
                    if hasattr(self.nvml, "nvmlDeviceSetFanSpeed_v2"):
                        # Se tiver permissões (modo admin ou desbloqueado), fica ativo
                        self.can_control_gpu_hardware = True
        except Exception:
            self.nvml = None
            self.nvml_device = None
            self.can_control_gpu_hardware = False

    def set_cpu_fan(self, percent, is_auto=False):
        """Define a velocidade alvo da ventoinha do CPU (0 a 100%)."""
        if is_auto:
            self.cpu_fan_auto = True
        else:
            self.cpu_fan_auto = False
            self.cpu_fan_target = max(10, min(100, int(percent)))
        return self.get_cpu_fan_stats()

    def set_gpu_fan(self, percent, is_auto=False):
        """Define a velocidade alvo da ventoinha da GPU (0 a 100%)."""
        if is_auto:
            self.gpu_fan_auto = True
            # Se suportado no hardware, restaurar modo automático do driver NVIDIA
            if self.nvml and self.nvml_device and hasattr(self.nvml, "nvmlDeviceSetDefaultFanSpeed_v2"):
                try:
                    self.nvml.nvmlDeviceSetDefaultFanSpeed_v2(self.nvml_device, 0)
                except Exception:
                    pass
        else:
            self.gpu_fan_auto = False
            self.gpu_fan_target = max(10, min(100, int(percent)))
            # Tentar aplicar no hardware NVIDIA se possível
            if self.nvml and self.nvml_device and hasattr(self.nvml, "nvmlDeviceSetFanSpeed_v2"):
                try:
                    self.nvml.nvmlDeviceSetFanSpeed_v2(self.nvml_device, 0, self.gpu_fan_target)
                except Exception:
                    pass
        return self.get_gpu_fan_stats()

    def apply_profile(self, profile_name):
        """Aplica um perfil de velocidade pré-definido."""
        name = profile_name.upper()
        if "AUTO" in name:
            self.set_cpu_fan(50, is_auto=True)
            self.set_gpu_fan(50, is_auto=True)
        elif "SILENC" in name or "QUIET" in name:
            self.set_cpu_fan(35, is_auto=False)
            self.set_gpu_fan(30, is_auto=False)
        elif "EQUILIB" in name or "BALANCE" in name:
            self.set_cpu_fan(55, is_auto=False)
            self.set_gpu_fan(50, is_auto=False)
        elif "GAME" in name or "GAMING" in name:
            self.set_cpu_fan(75, is_auto=False)
            self.set_gpu_fan(75, is_auto=False)
        elif "TURBO" in name or "100" in name:
            self.set_cpu_fan(100, is_auto=False)
            self.set_gpu_fan(100, is_auto=False)

    def get_cpu_rpm_for_pct(self, pct):
        """Calcula o RPM proporcional para uma dada percentagem."""
        pct_norm = max(0, min(100, pct)) / 100.0
        return int(self.cpu_min_rpm + (self.cpu_max_rpm - self.cpu_min_rpm) * pct_norm)

    def get_gpu_rpm_for_pct(self, pct):
        """Calcula o RPM proporcional para uma dada percentagem."""
        if pct <= 0:
            return 0
        pct_norm = max(0, min(100, pct)) / 100.0
        return int(self.gpu_min_rpm + (self.gpu_max_rpm - self.gpu_min_rpm) * pct_norm)

    def get_cpu_fan_stats(self):
        """Devolve dicionário com estado atual da ventoinha do CPU."""
        return {
            "auto": self.cpu_fan_auto,
            "target_pct": self.cpu_fan_target,
            "target_rpm": self.get_cpu_rpm_for_pct(self.cpu_fan_target)
        }

    def get_gpu_fan_stats(self):
        """Devolve dicionário com estado atual da ventoinha da GPU."""
        return {
            "auto": self.gpu_fan_auto,
            "target_pct": self.gpu_fan_target,
            "target_rpm": self.get_gpu_rpm_for_pct(self.gpu_fan_target)
        }
