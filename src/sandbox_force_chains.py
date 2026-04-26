from process_bond_strain import full_chain_figure, sequential_force_chain_figure
import matplotlib.pyplot as plt

#curves_info = [
#    (r"C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\results\093-FS\job12827898.16_dsu300_rho0.66_a75_link0.543_prestr0.0", r"$\mathcal{E}_f = 0$", 0.0),
#    (r"C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\results\093-FS\job12827898.16_dsu300_rho0.66_a75_link0.543_prestr0.2", r"$\mathcal{E}_f = 0.2$", 0.2),
#]

curves_info = [
    (r"C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\results\093-FS\job12939337.28_dsu300_rho0.62_a75_link0.521_prestr0.1", r"$\mathcal{E}_f = 0.1$", 0.1),
    (r"C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\results\093-FS\job12939337.28_dsu300_rho0.62_a75_link0.521_prestr0.2", r"$\mathcal{E}_f = 0.2$", 0.2),
    (r"C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\results\093-FS\job12939337.28_dsu300_rho0.62_a75_link0.521_prestr0.3", r"$\mathcal{E}_f = 0.3$", 0.3),
]

ax = plt.subplot()

sequential_force_chain_figure(curves_info, ax)