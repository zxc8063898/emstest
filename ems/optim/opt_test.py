# -*- coding: utf-8 -*-
"""
optimization for unit commitment of the household devices.

@author: ge57vam
"""
import sys
import pyomo.core as pyen
# import pyomo.environ
# from pyomo.core import *
from pyomo.opt import SolverFactory
from pyomo.opt import SolverManagerFactory
import pandas as pd
import numpy as np
import pyomo.core as py
import os
from scipy.interpolate import UnivariateSpline
import time as tm

from pyomo.environ import *
import matplotlib.pyplot as plt
import scipy.io

from ems.ems_mod import ems as ems_loc


def run_hp_opt(ems_local, plot_fig=True, result_folder='C:'):
    #    input_file = 'C:\Optimierung\Eingangsdaten_hp.xlsx'
    #    data = read_xlsdata(input_file);

    prob, timesteps = run_hp(ems_local)
    length = len(timesteps)

    print('Load Results ...\n')

    # electricity variable
    HP_ele_cap, HP_ele_run, elec_import, elec_export, lastprofil_elec, ev_pow, CHP_cap, pv_power, bat_cont, bat_power, bat_power_pos, bat_power_neg = \
        (np.zeros(length) for i in range(12));
    # heat variable
    boiler_cap, CHP_heat_cap, HP_heat_run, HP_heat_cap, CHP_op, HP_operation, lastprofil_heat, sto_e_pow, sto_e_pow_pos, sto_e_pow_neg, sto_e_cont = \
        (np.zeros(length) for i in range(11));
    # final cost

    cost_min = np.zeros(length)
    # heat balance

    bat_max_cont = value(prob.bat_cont_max)
    sto_cont_max = value(prob.sto_cont)
    bat_cont_init = bat_max_cont * 0.5
    sto_cont_init = sto_cont_max * 0.5

    i = 0

    # timesteps = sorted(get_entity(prob, 't').index)
    # demand, ext, pro, sto = get_timeseries(prob, timesteps

    for idx in timesteps:
        # electricity balance
        ev_pow[i] = value(prob.ev_power[idx]) * value(prob.ev_max_pow);
        elec_import[i] = value(prob.elec_import[idx]);
        elec_export[i] = value(prob.elec_export[idx]);
        lastprofil_elec[i] = value(prob.lastprofil_elec[idx]);
        CHP_op[i] = value(prob.CHP_cap[idx]);
        CHP_cap[i] = value(prob.CHP_cap[idx] * prob.chp_elec_max_cap);
        pv_power[i] = value(prob.PV_cap[idx] * prob.pv_effic * prob.solar[idx]);
        bat_cont[i] = value(prob.bat_cont[idx]);
        bat_power[i] = value(prob.bat_pow[idx]);

        ##heat balance
        boiler_cap[i] = value(prob.boiler_cap[idx]);
        CHP_heat_cap[i] = value(prob.CHP_cap[idx] * prob.chp_elec_max_cap / prob.chp_elec_effic * prob.chp_ther_effic);

        HP_operation[i] = value(prob.hp_run[idx] * prob.sto_max_cont) / value(prob.sto_max_cont)
        HP_heat_cap[i] = value(prob.hp_run[idx] * prob.hp_ther_pow[idx])
        HP_ele_cap[i] = value(prob.hp_run[idx] * prob.hp_ele_pow[idx])
        HP_heat_run[i] = value(prob.hp_ther_pow[idx])
        HP_ele_run[i] = value(prob.hp_ele_pow[idx])

        lastprofil_heat[i] = value(prob.lastprofil_heat[idx]);
        sto_e_pow[i] = value(prob.sto_e_pow[idx]);
        sto_e_cont[i] = value(prob.sto_e_cont[idx]);

        # the total cost
        cost_min[i] = value(prob.costs[idx]);

        i += 1;

        SOC_heat = sto_e_cont / sto_cont_max * 100;
        SOC_elec = bat_cont / bat_max_cont * 100;
    # battery_power

    for i in range(length):
        if bat_power[i] > 0:
            bat_power_neg[i] = -bat_power[i];
        else:
            bat_power_pos[i] = -bat_power[i];

    # heat storage power   
    for i in range(length):
        if sto_e_pow[i] > 0:
            sto_e_pow_neg[i] = -sto_e_pow[i];
        else:
            sto_e_pow_pos[i] = -sto_e_pow[i];

            # plt.plot(c)
    # plt.plot(a)
    # plt.plot(b)
    # plt.plot(d)

    ### plot elec balance
    N = len(timesteps)
    ind = np.arange(N)  # the x locations for the groups
    width = 1  # the width of the bars: can also be len(x) sequence

    print('Results Loaded.')
    # plt.clf()

    COLOURS = {
        0: 'lightsteelblue',
        1: 'cornflowerblue',
        2: 'royalblue',
        3: 'lightgreen',
        4: 'salmon',
        5: 'mediumseagreen',
        6: 'orchid',
        7: 'burlywood',
        8: 'palegoldenrod',
        9: 'darkkhaki',
        10: 'lightskyblue',
        11: 'firebrick',
        12: 'blue',
        13: 'darkgreen'}

    if plot_fig is True:
        fig = plt.figure()
        ax1 = fig.add_subplot(111)
        p1 = plt.bar(ind, CHP_cap, width, bottom=bat_power_pos, color='skyblue')
        ax1.axhline(linewidth=2, color="black")

        p2 = plt.bar(ind, pv_power, width,
                     bottom=bat_power_pos + CHP_cap, color='wheat')
        p3 = plt.bar(ind, bat_power_pos, width, color='#ff5a60')
        p4 = plt.bar(ind, bat_power_neg, width, color='#ff5a60')
        p5 = plt.bar(ind, elec_import, width, bottom=bat_power_pos + CHP_cap + pv_power, color='#689eb8')
        p6 = plt.bar(ind, -elec_export, width, bottom=bat_power_neg, color='black')
        # p7 = plt.plot(ind, lastprofil_elec,linewidth=3,color='k')
        p7 = plt.step(ind, lastprofil_elec, linewidth=2, where='mid', color='k')
        p8 = plt.bar(ind, -ev_pow, width, bottom=bat_power_neg - elec_export, color='pink')
        p9 = plt.bar(ind, -HP_ele_cap, width, bottom=bat_power_neg - elec_export - ev_pow, color='#a79b94')

        plt.xlabel('time [h]', fontsize=25)
        plt.ylabel('power und ele. demand [kW]', fontsize=25)
        plt.title('electricity balance', fontsize=30)
        idx_plt = np.arange(0, len(timesteps), int(len(timesteps) / 5))
        plt.xticks(ind[idx_plt], timesteps[idx_plt])
        ax1.set_xlim(0, len(timesteps) - 1)
        # plt.yticks(np.arange(-10, 10, 2))
        plt.legend((p1[0], p2[0], p3[0], p5[0], p6[0], p7[0], p8[0], p9[0]),
                   ('CHP', 'PV', 'battery', 'import', 'export', 'ele. demand', 'EV charge', 'HP'), prop={'size': 20},
                   loc='lower left')
        fig1 = plt.figure()
        ax2 = plt.subplot()
        # p8 = plt.plot(ind, bat_cont/bat_max_cont*100,linewidth=1,color='red')

        p8 = plt.step(ind, SOC_elec, linewidth=1, color='red', where='mid')
        plt.xlabel('time [h]', fontsize=25)
        plt.ylabel('SOC [%]', fontsize=25)
        plt.title('SOC of Battery', fontsize=30)
        plt.xticks(ind[idx_plt], timesteps[idx_plt])
        ax2.set_xlim(0, len(timesteps) - 1)
        plt.show()

    # plot heat balance
    if plot_fig is True:
        fig = plt.figure()
        ax1 = fig.add_subplot(111)
        ax1.axhline(linewidth=2, color="black")
        p1 = plt.bar(ind, boiler_cap, width, bottom=sto_e_pow_pos, color='#689eb8')
        p2 = plt.bar(ind, CHP_heat_cap, width,
                     bottom=boiler_cap + sto_e_pow_pos, color='skyblue')
        p3 = plt.bar(ind, HP_heat_cap, width, bottom=boiler_cap + CHP_heat_cap + sto_e_pow_pos, color='#a79b94')
        p4 = plt.bar(ind, sto_e_pow_pos, width, color='#ff5a60')
        p5 = plt.bar(ind, sto_e_pow_neg, width, color='#ff5a60')
        p6 = plt.step(ind, lastprofil_heat, linewidth=2, where='mid', color='k')

        plt.xlabel('time [1/4 h]', fontsize=25)
        plt.ylabel('power and heat load [kW]', fontsize=25)
        plt.title('heat balance', fontsize=30)
        plt.xticks([0, 24, 2, 2], fontsize=30)
        plt.yticks(fontsize=30)
        idx_plt = np.arange(0, len(timesteps), int(len(timesteps) / 5))
        plt.xticks(ind[idx_plt], timesteps[idx_plt])
        ax1.set_xlim(0, len(timesteps) - 1)
        # plt.yticks(np.arange(-10, 10, 2))
        plt.legend((p1[0], p2[0], p3[0], p4[0], p6[0]), ('boiler', 'CHP', 'HP', 'heat storage', 'heat demand'),
                   prop={'size': 20}, loc='lower left')
        fig1 = plt.figure()
        ax2 = plt.subplot()

        p7 = plt.step(ind, SOC_heat, linewidth=1, where='mid', color='red')
        plt.xlabel('time [h]', fontsize=25)
        plt.ylabel('SOC [%]', fontsize=25)
        plt.xticks(ind[idx_plt], timesteps[idx_plt])
        ax2.set_xlim(0, len(timesteps) - 1)
        plt.title('SOC of heat storage', fontsize=30)
        plt.show()

        # save the data
    from datetime import datetime

    print('Save Results to Reportfile...\n')

    # xx ="\\nas.ads.mwn.de\ge57vam\TUM-PC\Desktop\Unterlagen\result"
    # Create Name of Resultfile
    t0 = tm.time()
    # inputfilename = input_file
    now = datetime.now().strftime('%Y%m%dT%H%M')
    resultfile = os.path.join(result_folder, 'result-{}.xlsx'.format(now))
    writer = pd.ExcelWriter(resultfile)

    data_input = {'HP_operation': list(HP_operation), 'HP_heat_power': list(HP_heat_cap),
                  'HP_heat_run': list(HP_heat_run),
                  'HP_ele_run': list(HP_ele_run), 'CHP_operation': list(CHP_op), 'SOC_heat': list(SOC_heat),
                  'SOC_elec': list(SOC_elec),
                  'battery_SOC': list(bat_cont / bat_max_cont * 100), 'battery_power': list(bat_power),
                  'PV_power': list(pv_power),
                  'EV_power': list(ev_pow), 'min cost': list(cost_min)}

    df = pd.DataFrame(data=data_input)
    df.to_excel(writer, 'operation_plan', merge_cells=False)
    scipy.io.savemat('C:\Optimierung\AAAAA.mat', {'struct1': df.to_dict("list")})
    writer.save()  # save

    print('Results Saved. time: ' + "{:.1f}".format(tm.time() - t0) + ' s\n')

    return data_input


def run_hp(ems_local):
    # record the time
    t0 = tm.time()
    # get all the data from the external file
    # my_ems1 = ems_loc(initialize=True, path='C:/Users/ge57vam/emsflex/ems/ems01_ems.txt')
    my_ems1 = ems_local
    devices = my_ems1['devices']

    # read data from excel file


    print('Data Read. time: ' + "{:.1f}".format(tm.time() - t0) + ' s\n')

    print('Prepare Data ...\n')
    t = tm.time()

    # write in the time series from the data
    df_time_series = ems_local['fcst']
    time_series = pd.DataFrame.from_dict(df_time_series)
    # time = time_series.index.values

    print('Data Prepared. time: ' + "{:.1f}".format(tm.time() - t) + ' s\n')
    #    lastprofil =data['Lastprofil']
    #    source_import =data['import']
    #    source_export =data['export']


    # system
    # get the initial time step
    #time_step_initial = parameter.loc['System']['value']
    time_step_initial = 0
    timesteps_all = np.arange(1, 96)
    # timestep_1 = timesteps[0]

    timesteps = timesteps_all[time_step_initial:96]
    t_dn = 6
    t_up = 6
    timesteps_dn = timesteps[time_step_initial+1:96 - t_dn]
    timesteps_up = timesteps[time_step_initial+1:96 - t_up]

    # 15 min for every timestep/ timestep by one hour
    # create the concrete model
    p2e = 0.25

    # create the model object m
    m = pyen.ConcreteModel()

    # heat storage
    sto_param = devices['sto']
    # storage_cap = sto_param['stocap']
    tem_min_sto = sto_param['mintemp']
    tem_max_sto = sto_param['maxtemp']
    soc_init = sto_param['initSOC']
    self_discharge = sto_param['self_discharge']
    # unit in kWh
    sto_cont = sto_param['stocap']

    # boiler
    boil_param = devices['boiler']
    boil_cap = boil_param['maxpow']
    boil_eff = boil_param['eta']
    # EV, availability should be added
    ev_param = devices['ev']
    ev_max_power = ev_param['maxpow']
    # CHP
    chp_param = devices['chp']
    chp_elec_eff = chp_param['eta'][0]
    chp_ther_eff = chp_param['eta'][1]
    chp_elec_cap = chp_param['maxpow']
    # heat pump
    hp_param = devices['hp']
    hp_ther_cap = pd.DataFrame.from_dict(hp_param['maxpow'])
    hp_cop = pd.DataFrame.from_dict(hp_param['COP'])
    # PV
    pv_param = devices['pv']
    pv_peak_pow = pv_param['maxpow']
    pv_eff = pv_param['eta']
    # battery
    bat_param = devices['bat']
    bat_max_cont = bat_param['stocap']
    bat_SOC_init = bat_param['initSOC']
    bat_pow_max = bat_param['maxpow']

    ## create the parameter
    print('Define Model ...\n')
    #
    m.t = pyen.Set(ordered=True, initialize=timesteps,
                   doc='Timesteps with zero')

    #    m.t_end = pyen.Set(initialize=timesteps,
    #		doc='Timesteps without zero')
    m.t_DN = pyen.Set(ordered=True, initialize=timesteps_dn,
                      doc='Timesteps without zero')
    m.t_UP = pyen.Set(ordered=True, initialize=timesteps_up,
                      doc='Timesteps without zero')

    # heat_storage
    m.sto_max_cont = pyen.Param(initialize=sto_cont,
                                doc='No Partload: offset is zero')

    m.SOC_init = pyen.Param(initialize=soc_init,
                            doc='No Partload: offset is zero')

    # battery
    m.bat_cont_max = pyen.Param(initialize=bat_max_cont)
    m.bat_SOC_init = pyen.Param(initialize=bat_SOC_init)
    m.bat_power_max = pyen.Param(initialize=bat_pow_max)

    # hp
    m.hp_ther_pow = pyen.Param(m.t, initialize=1, mutable=True, within=pyen.NonNegativeReals,
                               doc='No Partload: offset is zero')
    m.sto_cont = pyen.Param(initialize=sto_cont,
                            doc='No Partload: offset is zero')
    m.hp_COP = pyen.Param(m.t, initialize=1, mutable=True, within=pyen.NonNegativeReals,
                          doc='No Partload: offset is zero')

    m.hp_ele_pow = pyen.Param(m.t, initialize=1, mutable=True, within=pyen.NonNegativeReals,
                              doc='No Partload: offset is zero')

    m.T_DN = pyen.Param(initialize=t_dn, mutable=True,
                        doc='No Partload: offset is zero')
    m.T_UP = pyen.Param(initialize=t_up, mutable=True,
                        doc='No Partload: offset is zero')

    # elec_vehicle
    m.ev_max_pow = pyen.Param(initialize=ev_max_power,
                              doc='No Partload: offset is zero')
    # boilder
    m.boiler_max_cap = pyen.Param(initialize=boil_cap,
                                  doc='No Partload: offset is zero')
    m.boiler_eff = pyen.Param(initialize=boil_eff,
                              doc='No Partload: offset is zero')
    # chp
    m.chp_elec_effic = pyen.Param(initialize=chp_elec_eff,
                                  doc='chp ele. efficiency')
    m.chp_ther_effic = pyen.Param(initialize=chp_ther_eff,
                                  doc='No Partload: offset is zero')
    m.chp_elec_max_cap = pyen.Param(initialize=chp_elec_cap,
                                    doc='No Partload: offset is zero')
    # solar
    m.pv_effic = pyen.Param(initialize=pv_eff,
                            doc='No Partload: offset is zero')
    m.pv_peak_power = pyen.Param(initialize=pv_peak_pow,
                                 doc='No Partload: offset is zero')
    m.solar = pyen.Param(m.t, initialize=1, mutable=True,
                         doc='No Partload: offset is zero')

    #    for t in m.t_UP:
    #        m.t_dn[t] = t_dn
    #        m.t_up[t] = t_dn

    # price
    m.ele_price_in, m.ele_price_out, m.gas_price = (pyen.Param(m.t, initialize=1, mutable=True) for i in range(3))

    # lastprofil
    m.lastprofil_heat, m.lastprofil_elec = (pyen.Param(m.t, initialize=1, mutable=True) for i in range(2))

    for t in m.t:
        # weather data
        m.ele_price_in[t] = time_series.loc[t]['ele_price_in']
        m.gas_price[t] = time_series.loc[t]['gas']
        m.ele_price_out[t] = time_series.loc[t]['ele_price_out']
        m.lastprofil_heat[t] = time_series.loc[t]['last_heat']
        m.lastprofil_elec[t] = time_series.loc[t]['last_elec']
        m.solar[t] = time_series.loc[t]['solar']

        # calculate the spline function for thermal power of heat pump
        spl_ther_pow = UnivariateSpline(list(map(float, hp_ther_cap.columns.values)), list(hp_ther_cap.iloc[0, :]))
        m.hp_ther_pow[t] = int(spl_ther_pow(time_series.loc[t]['temp'] + 273.15))
        # calculate the spline function for COP of heat pump
        spl_cop = UnivariateSpline(list(map(float, hp_cop.columns.values)), list(hp_cop.iloc[0, :]))
        m.hp_COP[t] = int(spl_cop(time_series.loc[t]['temp'] + 273.15))
        m.hp_ele_pow[t] = m.hp_ther_pow[t] / m.hp_COP[t]

    # m.ele_price = ele_price

    # Variables

    m.hp_run = pyen.Var(m.t, within=pyen.Boolean,
                        doc='operation of the heat pump')
    m.CHP_cap = pyen.Var(m.t, within=pyen.Boolean,
                         doc='operation of the CHP')

    m.ev_power = pyen.Var(m.t, within=pyen.Boolean,
                          doc='operation of the EV')
    m.boiler_cap, m.PV_cap, m.elec_import, m.elec_export, m.costs, m.bat_cont, m.sto_e_cont = \
        (pyen.Var(m.t, within=pyen.NonNegativeReals) for i in range(7))
    m.bat_pow, m.sto_e_pow = (pyen.Var(m.t, within=pyen.Reals) for i in range(2))

    # Constrains

    # heat_storage
    def sto_e_cont_def_rule(m, t):
        if t > m.t[1]:
            return m.sto_e_cont[t] == m.sto_e_cont[t - 1] + m.sto_e_pow[t] * p2e;
        else:
            return m.sto_e_cont[t] == m.sto_max_cont * m.SOC_init / 100 + m.sto_e_pow[t] * p2e;

    m.sto_e_cont_def = pyen.Constraint(m.t,
                                       rule=sto_e_cont_def_rule,
                                       doc='heat_storage_balance')

    def heat_balance_rule(m, t):
        return m.boiler_cap[t] + m.CHP_cap[t] * m.chp_elec_max_cap / m.chp_elec_effic * m.chp_ther_effic + \
               m.hp_run[t] * m.hp_ther_pow[t] - m.lastprofil_heat[t] - m.sto_e_pow[t] == 0;

    m.heat_power_balance = pyen.Constraint(m.t,
                                           rule=heat_balance_rule,
                                           doc='heat_storage_balance')

    # battery
    def battery_e_cont_def_rule(m, t):
        if t > m.t[1]:
            return m.bat_cont[t] == m.bat_cont[t - 1] + m.bat_pow[t] * p2e;
        else:
            return m.bat_cont[t] == m.bat_cont_max * m.bat_SOC_init / 100 + m.bat_pow[t] * p2e;

    m.bat_e_cont_def = pyen.Constraint(m.t,
                                       rule=battery_e_cont_def_rule,
                                       doc='battery_balance')

    def elec_balance_rule(m, t):
        return m.elec_import[t] + m.CHP_cap[t] * m.chp_elec_max_cap + m.PV_cap[t] * m.pv_effic * m.solar[t] - \
               m.elec_export[t] - m.hp_run[t] * m.hp_ele_pow[t] - m.lastprofil_elec[t] - \
               m.bat_pow[t] - m.ev_power[t] * m.ev_max_pow == 0;

    m.elec_power_balance = pyen.Constraint(m.t,
                                           rule=elec_balance_rule,
                                           doc='elec_balance')

    def cost_sum_rule(m, t):
        return m.costs[t] == p2e * (m.boiler_cap[t] / m.boiler_eff * m.gas_price[t] \
                                    + m.CHP_cap[t] * m.chp_elec_max_cap / m.chp_elec_effic * m.gas_price[t] +
                                    m.elec_import[t] * m.ele_price_in[t] \
                                    - m.elec_export[t] * m.ele_price_out[t]);

    m.cost_sum = pyen.Constraint(m.t,
                                 rule=cost_sum_rule)

    ##processes
    # EV
    def EV_cap_max_rule(m, t):
        if t > m.t[int(len(m.t) / 2)]:
            # return pyen.Constraint.Skip;
            return m.ev_power[t] <= 0
        else:
            return m.ev_power[t] <= 0

    # m.EV_cap_max_def= pyen.Constraint(m.t,
    # rule = EV_cap_max_rule)

    #    def EV_cap_min_rule(m,t):
    #        if t < m.t[int(len(m.t)/2)]:
    #          return m.ev_power[t] >= m.ev_max_pow;
    #        else:
    #          return pyen.Constraint.Skip;
    #
    #    m.EV_cap_min_def= pyen.Constraint(m.t,
    #			rule = EV_cap_min_rule)

    def EV_cont_rule(m):
        return pyen.summation(m.ev_power) >= 4;

    m.EV_cont_def = pyen.Constraint(rule=EV_cont_rule)

    # CHP
    def chp_max_cap_rule(m, t):
        return m.CHP_cap[t] <= m.chp_elec_max_cap;

    m.chp_max_cap_def = pyen.Constraint(m.t,
                                        rule=chp_max_cap_rule)

    ##hp
    def hp_min_still_t_rule(m, t):
        return (m.hp_run[t - 1] - m.hp_run[t]) * m.T_DN <= m.T_DN - (
                m.hp_run[t] + m.hp_run[t + 1] + m.hp_run[t + 2] + m.hp_run[t + 3] + m.hp_run[t + 4] + m.hp_run[
            t + 5]);

    m.hp_min_still_t_def = pyen.Constraint(m.t_DN,
                                           rule=hp_min_still_t_rule)

    def hp_min_lauf_t_rule(m, t):

        return (m.hp_run[t] - m.hp_run[t - 1]) * m.T_UP <= m.hp_run[t] + m.hp_run[t + 1] + m.hp_run[t + 2] + m.hp_run[
            t + 3] + m.hp_run[t + 4] + m.hp_run[t + 5];

    #  return (m.hp_run[t]-m.hp_run[t-1])*m.t_up[t] <= m.t_up[t]; m.hp_run[k]
    m.hp_min_lauf_t_def = pyen.Constraint(m.t_UP,
                                          rule=hp_min_lauf_t_rule)

    def chp_min_still_t_rule(m, t):
        return (m.CHP_cap[t - 1] - m.CHP_cap[t]) * m.T_DN <= m.T_DN - (
                m.CHP_cap[t] + m.CHP_cap[t + 1] + m.CHP_cap[t + 2] + m.CHP_cap[t + 3] + m.CHP_cap[t + 4] +
                m.CHP_cap[t + 5]);

    m.chp_min_still_t_def = pyen.Constraint(m.t_DN,
                                            rule=chp_min_still_t_rule)

    def chp_min_lauf_t_rule(m, t):

        return (m.CHP_cap[t] - m.CHP_cap[t - 1]) * m.T_UP <= m.CHP_cap[t] + m.CHP_cap[t + 1] + m.CHP_cap[t + 2] + \
               m.CHP_cap[t + 3] + m.CHP_cap[t + 4] + m.CHP_cap[t + 5];

    #  return (m.hp_run[t]-m.hp_run[t-1])*m.t_up[t] <= m.t_up[t]; m.hp_run[k]
    m.chp_min_lauf_t_def = pyen.Constraint(m.t_UP,
                                           rule=chp_min_lauf_t_rule)

    # boiler
    def boiler_max_cap_rule(m, t):
        return m.boiler_cap[t] <= m.boiler_max_cap;

    m.boiler_max_cap_def = pyen.Constraint(m.t,
                                           rule=boiler_max_cap_rule)

    # PV
    def pv_max_cap_rule(m, t):
        return m.PV_cap[t] <= m.pv_peak_power;

    m.pv_max_cap_def = pyen.Constraint(m.t,
                                       rule=pv_max_cap_rule)

    # elec_import
    def elec_import_rule(m, t):
        return m.elec_import[t] <= 50 * 5000;

    m.elec_import_def = pyen.Constraint(m.t,
                                        rule=elec_import_rule)

    # elec_export
    def elec_export_rule(m, t):
        return m.elec_export[t] <= 50 * 5000;

    m.elec_export_def = pyen.Constraint(m.t,
                                        rule=elec_export_rule)

    ##storage
    # storage content
    def sto_e_cont_min_rule(m, t):
        return m.sto_e_cont[t] / m.sto_cont >= 0.1;

    m.sto_e_cont_min = pyen.Constraint(m.t,
                                       rule=sto_e_cont_min_rule)

    def sto_e_cont_max_rule(m, t):
        return m.sto_e_cont[t] / m.sto_cont <= 0.9;

    m.sto_e_cont_max = pyen.Constraint(m.t,
                                       rule=sto_e_cont_max_rule)

    def bat_e_cont_min_rule(m, t):
        return m.bat_cont[t] / m.bat_cont_max >= 0.1;

    m.bat_e_cont_min = pyen.Constraint(m.t,
                                       rule=bat_e_cont_min_rule)

    def bat_e_cont_max_rule(m, t):
        return m.bat_cont[t] / m.bat_cont_max <= 0.9;

    m.bat_e_cont_max = pyen.Constraint(m.t,
                                       rule=bat_e_cont_max_rule)

    # storage power

    def sto_e_max_pow_rule_1(m, t):
        return m.sto_e_pow[t] <= m.sto_cont;

    m.sto_e_pow_max_1 = pyen.Constraint(m.t,
                                        rule=sto_e_max_pow_rule_1)

    def sto_e_max_pow_rule_2(m, t):
        return m.sto_e_pow[t] >= -m.sto_cont;

    m.sto_e_pow_max_2 = pyen.Constraint(m.t,
                                        rule=sto_e_max_pow_rule_2)

    def bat_e_max_pow_rule_1(m, t):
        return m.bat_pow[t] <= m.bat_power_max;

    m.bat_e_pow_max_1 = pyen.Constraint(m.t,
                                        rule=bat_e_max_pow_rule_1)

    def bat_e_max_pow_rule_2(m, t):
        return m.bat_pow[t] >= -m.bat_power_max;

    m.bat_e_pow_max_2 = pyen.Constraint(m.t,
                                        rule=bat_e_max_pow_rule_2)

    ##end state of storage and battery

    m.sto_e_cont_end = pyen.Constraint(expr=(m.sto_e_cont[m.t[-1]] >= 0.5 * m.sto_cont))
    m.bat_e_cont_end = pyen.Constraint(expr=(m.bat_cont[m.t[-1]] >= 0.5 * m.bat_cont_max))

    # m.sto_e_cont_initial = pyen.Constraint(expr=(m.sto_e_cont[m.t0] == 0.5))
    # m.cc_bal = pyen.Constraint(expr=(pyen.summation(m.hp_run) >= 4))

    def obj_rule(m):
        # Return sum of total costs over all cost types.
        # Simply calculates the sum of m.costs over all m.cost_types.
        return pyen.summation(m.costs)

    m.obj = pyen.Objective(
        sense=pyen.minimize,
        rule=obj_rule,
        doc='Sum costs by cost type')

    print('Model Defined. time: ' + "{:.1f}".format(tm.time() - t) + ' s\n')
    print('Solve Model ...\n')
    optimizer = SolverFactory('glpk')
    solver_opt = dict()
    # solver_opt['SolTimeLimit'] = 50
    solver_opt['mipgap'] = 0.001
    # solver_manager = SolverManagerFactory('neos')
    # result = solver_manager.solve(m,opt=optimizer,tee=True,load_solutions=True)
    optimizer.solve(m, load_solutions=True, options=solver_opt, timelimit=15)
    # m.solutions.load_from(result);
    print('Model Solved. time: ' + "{:.1f}".format(tm.time() - t) + ' s\n')
    return m, timesteps


def read_xlsdata(input_file):
    # read sheets of excel file and put them in one dictionary xls_data
    xls = pd.ExcelFile(input_file)  # read excel file

    xls_data = {}  # create dictionary
    xls_data.update({'input_file': input_file})
    xls_data.update({'time_series': xls.parse('time_series').set_index(['time'])})
    xls_data.update({'parameter': xls.parse('Einstellung').set_index(['process'])})

    ## neue Sheet am 10.09.2018 for variable COP

    return xls_data


if __name__ == "__main__":
    # 3th argument for input file, and 4th argument for the result folder (dont have to be the same)
    run_hp_opt('C:\Optimierung\Eingangsdaten_hp.xlsx', 'C:\Optimierung')
