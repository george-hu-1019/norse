from typing import Tuple
import numpy as np
import torch

from ..functional.lif import LIFState, LIFFeedForwardState

from ..functional.lif_refrac import (
    LIFRefracParameters,
    LIFRefracState,
    LIFRefracFeedForwardState,
    lif_refrac_step,
    lif_refrac_feed_forward_step,
)


class LIFRefracCell(torch.nn.Module):
    """Module that computes a single euler-integration step of a LIF
    neuron-model with absolute refractory period. More specifically it
    implements one integration step of the following ODE.

    .. math::
        \\begin{align*}
            \dot{v} &= 1/\\tau_{\\text{mem}} (1-\Theta(\\rho)) \
            (v_{\\text{leak}} - v + i) \\\\
            \dot{i} &= -1/\\tau_{\\text{syn}} i \\\\
            \dot{\\rho} &= -1/\\tau_{\\text{refrac}} \Theta(\\rho)
        \end{align*}

    together with the jump condition

    .. math::
        \\begin{align*}
            z &= \Theta(v - v_{\\text{th}}) \\\\
            z_r &= \Theta(-\\rho)
        \end{align*}

    and transition equations

    .. math::
        \\begin{align*}
            v &= (1-z) v + z v_{\\text{reset}} \\\\
            i &= i + w_{\\text{input}} z_{\\text{in}} \\\\
            i &= i + w_{\\text{rec}} z_{\\text{rec}} \\\\
            \\rho &= \\rho + z_r \\rho_{\\text{reset}}
        \end{align*}

    where :math:`z_{\\text{rec}}` and :math:`z_{\\text{in}}` are the
    recurrent and input spikes respectively.

    Parameters:
        input (torch.Tensor): the input spikes at the current time step
        s (LIFRefracState): state at the current time step
        input_weights (torch.Tensor): synaptic weights for incoming spikes
        recurrent_weights (torch.Tensor): synaptic weights for recurrent spikes
        p (LIFRefracParameters): parameters of the lif neuron
        dt (float): Integration timestep to use

    Examples:

        >>> batch_size = 16
        >>> lif = LIFRefracCell(10, 20)
        >>> input = torch.randn(batch_size, 10)
        >>> s0 = lif.initial_state(batch_size)
        >>> output, s0 = lif(input, s0)
    """

    def __init__(
        self,
        input_size,
        hidden_size,
        parameters: LIFRefracParameters = LIFRefracParameters(),
        dt: float = 0.001,
    ):
        super(LIFRefracCell, self).__init__()
        self.input_weights = torch.nn.Parameter(
            torch.randn(hidden_size, input_size) / np.sqrt(input_size)
        )
        self.recurrent_weights = torch.nn.Parameter(
            torch.randn(hidden_size, hidden_size) / np.sqrt(hidden_size)
        )
        self.hidden_size = hidden_size
        self.parameters = parameters
        self.dt = dt

    def initial_state(self, batch_size, device, dtype=torch.float) -> LIFRefracState:
        return LIFRefracState(
            lif=LIFState(
                z=torch.zeros(batch_size, self.hidden_size, device=device, dtype=dtype),
                v=torch.zeros(batch_size, self.hidden_size, device=device, dtype=dtype),
                i=torch.zeros(batch_size, self.hidden_size, device=device, dtype=dtype),
            ),
            rho=torch.zeros(batch_size, self.hidden_size, device=device, dtype=dtype),
        )

    def forward(
        self, input_tensor: torch.Tensor, state: LIFRefracState
    ) -> Tuple[torch.Tensor, LIFRefracState]:
        return lif_refrac_step(
            input_tensor,
            state,
            self.input_weights,
            self.recurrent_weights,
            parameters=self.parameters,
            dt=self.dt,
        )


class LIFRefracFeedForwardCell(torch.nn.Module):
    """Module that computes a single euler-integration step of a
    LIF neuron-model with absolute refractory period. More specifically
    it implements one integration step of the following ODE.

    .. math::
        \\begin{align*}
            \dot{v} &= 1/\\tau_{\\text{mem}} (1-\Theta(\\rho)) \
            (v_{\\text{leak}} - v + i) \\\\
            \dot{i} &= -1/\\tau_{\\text{syn}} i \\\\
            \dot{\\rho} &= -1/\\tau_{\\text{refrac}} \Theta(\\rho)
        \end{align*}

    together with the jump condition

    .. math::
        \\begin{align*}
            z &= \Theta(v - v_{\\text{th}}) \\\\
            z_r &= \Theta(-\\rho)
        \end{align*}

    and transition equations

    .. math::
        \\begin{align*}
            v &= (1-z) v + z v_{\\text{reset}} \\\\
            \\rho &= \\rho + z_r \\rho_{\\text{reset}}
        \end{align*}

    Parameters:
        shape: Shape of the processed spike input
        parameters (LIFRefracParameters): parameters of the lif neuron
        dt (float): Integration timestep to use

    Examples:
        >>> batch_size = 16
        >>> lif = LIFRefracFeedForwardCell((20, 30))
        >>> input = torch.randn(batch_size, 20, 30)
        >>> s0 = lif.initial_state(batch_size)
        >>> output, s0 = lif(input, s0)
    """

    def __init__(
        self,
        shape,
        parameters: LIFRefracParameters = LIFRefracParameters(),
        dt: float = 0.001,
    ):
        super(LIFRefracFeedForwardCell, self).__init__()
        self.shape = shape
        self.parameters = parameters
        self.dt = dt

    def initial_state(self, batch_size, device, dtype) -> LIFFeedForwardState:
        return LIFRefracFeedForwardState(
            LIFFeedForwardState(
                v=torch.zeros(batch_size, *self.shape, device=device, dtype=dtype),
                i=torch.zeros(batch_size, *self.shape, device=device, dtype=dtype),
            ),
            rho=torch.zeros(batch_size, *self.shape, device=device, dtype=dtype),
        )

    def forward(
        self, input_tensor: torch.Tensor, state: LIFRefracFeedForwardState
    ) -> Tuple[torch.Tensor, LIFRefracFeedForwardState]:
        return lif_refrac_feed_forward_step(
            input_tensor, state, parameters=self.parameters, dt=self.dt
        )
